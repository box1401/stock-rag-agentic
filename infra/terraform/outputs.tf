output "api_url" {
  description = "Public URL of the api Cloud Run service"
  value       = google_cloud_run_v2_service.api.uri
}

output "web_url" {
  description = "Public URL of the web Cloud Run service"
  value       = google_cloud_run_v2_service.web.uri
}

output "reranker_url" {
  description = "Internal URL of the reranker Cloud Run service"
  value       = google_cloud_run_v2_service.reranker.uri
}

output "artifact_registry" {
  description = "Docker registry path. Use as `<repo>/<image>:<tag>`."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker.repository_id}"
}

output "reports_bucket" {
  description = "GCS bucket for generated reports"
  value       = google_storage_bucket.reports.name
}
