variable "project_id" {
  description = "GCP project id (e.g. compass-equity-prod)"
  type        = string
}

variable "region" {
  description = "Primary region. asia-east1 = closest to TW with full Cloud Run + Vertex coverage."
  type        = string
  default     = "asia-east1"
}

variable "github_repo" {
  description = "GitHub repository in 'owner/repo' form, used for Workload Identity Federation."
  type        = string
  default     = "box1401/stock-rag-agentic"
}

variable "image_tag" {
  description = "Image tag deployed to Cloud Run (set by GitHub Actions to commit SHA)."
  type        = string
  default     = "latest"
}

variable "artifact_registry_id" {
  description = "Artifact Registry repository id (single docker repo for the project)."
  type        = string
  default     = "compass"
}

# ---------- Cloud Run sizing knobs ----------

variable "api_cpu" {
  type    = string
  default = "1"
}

variable "api_memory" {
  type    = string
  default = "1Gi"
}

variable "api_min_instances" {
  type    = number
  default = 0
}

variable "api_max_instances" {
  type    = number
  default = 3
}

variable "web_cpu" {
  type    = string
  default = "1"
}

variable "web_memory" {
  type    = string
  default = "512Mi"
}

variable "web_min_instances" {
  type    = number
  default = 0
}

variable "web_max_instances" {
  type    = number
  default = 3
}

variable "reranker_cpu" {
  type    = string
  default = "2"
}

variable "reranker_memory" {
  type    = string
  default = "2Gi"
}

variable "reranker_min_instances" {
  description = "Set to 1 to keep model warm (costs money). 0 = scale-to-zero with ~1min cold start."
  type        = number
  default     = 0
}

variable "reranker_max_instances" {
  type    = number
  default = 2
}
