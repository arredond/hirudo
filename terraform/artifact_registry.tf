resource "google_artifact_registry_repository" "hirudo" {
  repository_id = "hirudo"
  format        = "DOCKER"
  location      = var.gcp_region
  description   = "ETL job image for the blood donation points pipeline"

  depends_on = [google_project_service.apis]
}
