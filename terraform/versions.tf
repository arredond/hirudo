terraform {
  required_version = ">= 1.7"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  # State starts local. Once you're happy with the setup, consider moving it
  # to a GCS bucket for durability:
  #   backend "gcs" {
  #     bucket = "donde-donar-422906-tfstate"
  #     prefix = "hirudo"
  #   }
}

provider "google" {
  project = var.gcp_project
  region  = var.gcp_region
}
