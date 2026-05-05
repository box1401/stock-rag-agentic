locals {
  required_apis = [
    "artifactregistry.googleapis.com",
    "run.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "secretmanager.googleapis.com",
    "storage.googleapis.com",
    "cloudtasks.googleapis.com",
    "cloudscheduler.googleapis.com",
    "sts.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
  ]

  # ENV var name in the api container -> Secret Manager secret_id
  api_secret_env = {
    GEMINI_API_KEY            = google_secret_manager_secret.all["gemini_api_key"].secret_id
    TAVILY_API_KEY            = google_secret_manager_secret.all["tavily_api_key"].secret_id
    SUPABASE_JWT_SECRET       = google_secret_manager_secret.all["supabase_jwt_secret"].secret_id
    SUPABASE_URL              = google_secret_manager_secret.all["supabase_url"].secret_id
    SUPABASE_ANON_KEY         = google_secret_manager_secret.all["supabase_anon_key"].secret_id
    SUPABASE_SERVICE_ROLE_KEY = google_secret_manager_secret.all["supabase_service_role_key"].secret_id
    DATABASE_URL              = google_secret_manager_secret.all["database_url"].secret_id
    LANGFUSE_PUBLIC_KEY       = google_secret_manager_secret.all["langfuse_public_key"].secret_id
    LANGFUSE_SECRET_KEY       = google_secret_manager_secret.all["langfuse_secret_key"].secret_id
    FINMIND_TOKEN             = google_secret_manager_secret.all["finmind_token"].secret_id
  }
}

resource "google_project_service" "enabled" {
  for_each                   = toset(local.required_apis)
  service                    = each.value
  disable_dependent_services = false
  disable_on_destroy         = false
}
