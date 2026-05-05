resource "google_artifact_registry_repository" "docker" {
  location      = var.region
  repository_id = var.artifact_registry_id
  description   = "Compass Equity container images"
  format        = "DOCKER"

  cleanup_policies {
    id     = "keep-recent-10"
    action = "KEEP"
    most_recent_versions {
      keep_count = 10
    }
  }

  cleanup_policies {
    id     = "delete-old-untagged"
    action = "DELETE"
    condition {
      tag_state  = "UNTAGGED"
      older_than = "604800s" # 7 days
    }
  }

  depends_on = [google_project_service.enabled]
}
