# --- Secret Manager ---
# Terraform creates the secret containers; secret VALUES are seeded by
# infra/scripts/seed-secrets.sh. Storing values in tfvars would commit them
# to git, which is what we are explicitly avoiding.

locals {
  secret_ids = {
    gemini_api_key            = "gemini-api-key"
    tavily_api_key            = "tavily-api-key"
    supabase_jwt_secret       = "supabase-jwt-secret"
    supabase_url              = "supabase-url"
    supabase_anon_key         = "supabase-anon-key"
    supabase_service_role_key = "supabase-service-role-key"
    database_url              = "database-url"
    langfuse_public_key       = "langfuse-public-key"
    langfuse_secret_key       = "langfuse-secret-key"
    finmind_token             = "finmind-token"
  }
}

resource "google_secret_manager_secret" "all" {
  for_each  = local.secret_ids
  secret_id = each.value

  replication {
    auto {}
  }

  depends_on = [google_project_service.enabled]
}

# Grant the api runtime SA read-access to every secret it consumes
resource "google_secret_manager_secret_iam_member" "api_accessor" {
  for_each = local.api_secret_env

  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api_runtime.email}"
}
