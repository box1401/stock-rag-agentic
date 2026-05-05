resource "random_id" "bucket_suffix" {
  byte_length = 3
}

resource "google_storage_bucket" "reports" {
  name                        = "${var.project_id}-reports-${random_id.bucket_suffix.hex}"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  versioning { enabled = false }

  lifecycle_rule {
    action { type = "Delete" }
    condition { age = 365 }
  }

  depends_on = [google_project_service.enabled]
}

resource "google_storage_bucket_iam_member" "api_writer" {
  bucket = google_storage_bucket.reports.name
  role   = "roles/storage.objectUser"
  member = "serviceAccount:${google_service_account.api_runtime.email}"
}
