# Artifact Registry repo is created by infra/scripts/bootstrap.sh because
# the deploy workflow needs to push images BEFORE Terraform applies the
# rest of the infrastructure. We read the existing repo as a data source
# so cloudrun.tf can build the image URL from it.

data "google_artifact_registry_repository" "docker" {
  location      = var.region
  repository_id = var.artifact_registry_id
}
