locals {
  ar_repo        = data.google_artifact_registry_repository.docker.repository_id
  api_image      = "${var.region}-docker.pkg.dev/${var.project_id}/${local.ar_repo}/api:${var.image_tag}"
  web_image      = "${var.region}-docker.pkg.dev/${var.project_id}/${local.ar_repo}/web:${var.image_tag}"
  reranker_image = "${var.region}-docker.pkg.dev/${var.project_id}/${local.ar_repo}/reranker:${var.image_tag}"
}

# --- API ---
resource "google_cloud_run_v2_service" "api" {
  name                = "compass-api"
  location            = var.region
  deletion_protection = false
  ingress             = "INGRESS_TRAFFIC_ALL"

  template {
    service_account                  = google_service_account.api_runtime.email
    timeout                          = "300s"
    max_instance_request_concurrency = 40

    scaling {
      min_instance_count = var.api_min_instances
      max_instance_count = var.api_max_instances
    }

    containers {
      image = local.api_image
      ports { container_port = 8000 }

      resources {
        limits = {
          cpu    = var.api_cpu
          memory = var.api_memory
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      env {
        name  = "ENV"
        value = "production"
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.region
      }
      env {
        name  = "GEMINI_MODEL_PRIMARY"
        value = "gemini-2.5-flash"
      }
      env {
        name  = "GEMINI_MODEL_FALLBACK"
        value = "gemini-2.5-flash-lite"
      }
      env {
        name  = "EMBEDDING_MODEL"
        value = "gemini-embedding-001"
      }
      env {
        name  = "RERANKER_URL"
        value = "${google_cloud_run_v2_service.reranker.uri}/rerank"
      }
      env {
        name  = "REPORTS_BUCKET"
        value = google_storage_bucket.reports.name
      }
      env {
        name  = "RATE_LIMIT_PER_MINUTE"
        value = "20"
      }

      dynamic "env" {
        for_each = local.api_secret_env
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value
              version = "latest"
            }
          }
        }
      }

      startup_probe {
        http_get { path = "/health" }
        initial_delay_seconds = 5
        period_seconds        = 10
        failure_threshold     = 6
      }
    }
  }

  depends_on = [google_project_service.enabled]
}

resource "google_cloud_run_v2_service_iam_member" "api_public" {
  name     = google_cloud_run_v2_service.api.name
  location = google_cloud_run_v2_service.api.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# --- Web ---
resource "google_cloud_run_v2_service" "web" {
  name                = "compass-web"
  location            = var.region
  deletion_protection = false
  ingress             = "INGRESS_TRAFFIC_ALL"

  template {
    service_account                  = google_service_account.web_runtime.email
    timeout                          = "60s"
    max_instance_request_concurrency = 80

    scaling {
      min_instance_count = var.web_min_instances
      max_instance_count = var.web_max_instances
    }

    containers {
      image = local.web_image
      ports { container_port = 3000 }

      resources {
        limits = {
          cpu    = var.web_cpu
          memory = var.web_memory
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      env {
        name  = "NODE_ENV"
        value = "production"
      }
      env {
        name  = "NEXT_PUBLIC_API_URL"
        value = google_cloud_run_v2_service.api.uri
      }
    }
  }

  depends_on = [google_project_service.enabled]
}

resource "google_cloud_run_v2_service_iam_member" "web_public" {
  name     = google_cloud_run_v2_service.web.name
  location = google_cloud_run_v2_service.web.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# --- Reranker ---
# Public is fine — no secrets. Could be locked to api SA later.
resource "google_cloud_run_v2_service" "reranker" {
  name                = "compass-reranker"
  location            = var.region
  deletion_protection = false
  ingress             = "INGRESS_TRAFFIC_ALL"

  template {
    service_account                  = google_service_account.reranker_runtime.email
    timeout                          = "120s"
    max_instance_request_concurrency = 4

    scaling {
      min_instance_count = var.reranker_min_instances
      max_instance_count = var.reranker_max_instances
    }

    containers {
      image = local.reranker_image
      ports { container_port = 8001 }

      resources {
        limits = {
          cpu    = var.reranker_cpu
          memory = var.reranker_memory
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      env {
        name  = "RERANKER_DEVICE"
        value = "cpu"
      }
      env {
        name  = "RERANKER_MODEL"
        value = "BAAI/bge-reranker-v2-m3"
      }

      startup_probe {
        http_get { path = "/health" }
        initial_delay_seconds = 30
        period_seconds        = 10
        timeout_seconds       = 5
        failure_threshold     = 12
      }
    }
  }

  depends_on = [google_project_service.enabled]
}

resource "google_cloud_run_v2_service_iam_member" "reranker_public" {
  name     = google_cloud_run_v2_service.reranker.name
  location = google_cloud_run_v2_service.reranker.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
