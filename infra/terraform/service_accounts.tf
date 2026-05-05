# --- Runtime service accounts (one per Cloud Run service) ---

resource "google_service_account" "api_runtime" {
  account_id   = "compass-api-runtime"
  display_name = "Compass Equity api runtime SA"
}

resource "google_service_account" "web_runtime" {
  account_id   = "compass-web-runtime"
  display_name = "Compass Equity web runtime SA"
}

resource "google_service_account" "reranker_runtime" {
  account_id   = "compass-reranker-runtime"
  display_name = "Compass Equity reranker runtime SA"
}

# --- Project-level roles for the api runtime ---

resource "google_project_iam_member" "api_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.api_runtime.email}"
}

resource "google_project_iam_member" "api_monitoring" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.api_runtime.email}"
}

resource "google_project_iam_member" "api_aiplatform_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.api_runtime.email}"
}

resource "google_project_iam_member" "api_tasks_enqueuer" {
  project = var.project_id
  role    = "roles/cloudtasks.enqueuer"
  member  = "serviceAccount:${google_service_account.api_runtime.email}"
}

# --- Web runtime: minimal — just logging ---

resource "google_project_iam_member" "web_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.web_runtime.email}"
}

# --- Reranker: just logging ---

resource "google_project_iam_member" "reranker_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.reranker_runtime.email}"
}
