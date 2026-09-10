data "google_project" "this" {
  project_id = var.gcp_project
}

# Runtime identity for the ETL job itself — only needs to read the secrets it uses.
resource "google_service_account" "etl_runtime" {
  account_id   = "hirudo-etl-runtime"
  display_name = "hirudo ETL Cloud Run Job runtime"
}

# Identity Cloud Scheduler uses to invoke the Cloud Run Job.
resource "google_service_account" "scheduler_invoker" {
  account_id   = "hirudo-etl-scheduler"
  display_name = "hirudo ETL Cloud Scheduler invoker"
}

# The default Cloud Build service account (created automatically once the
# Cloud Build API is enabled). It builds the image, pushes it, and updates
# the Job to point at the new image.
locals {
  cloudbuild_sa = "${data.google_project.this.number}@cloudbuild.gserviceaccount.com"
}

resource "google_project_iam_member" "cloudbuild_artifact_writer" {
  project = var.gcp_project
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${local.cloudbuild_sa}"
}

resource "google_project_iam_member" "cloudbuild_run_developer" {
  project = var.gcp_project
  role    = "roles/run.developer"
  member  = "serviceAccount:${local.cloudbuild_sa}"
}

# Cloud Build deploys the Job as etl_runtime, so it needs to "act as" it.
resource "google_service_account_iam_member" "cloudbuild_acts_as_runtime" {
  service_account_id = google_service_account.etl_runtime.name
  role                = "roles/iam.serviceAccountUser"
  member              = "serviceAccount:${local.cloudbuild_sa}"
}
