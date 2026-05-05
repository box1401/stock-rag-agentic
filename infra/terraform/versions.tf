terraform {
  required_version = ">= 1.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.13"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 6.13"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  backend "gcs" {
    # bucket = "<project-id>-tfstate"   # set via -backend-config at init time
    prefix = "compass-equity"
  }
}
