resource "google_cloud_run_v2_job_iam_member" "scheduler_can_run" {
  name     = google_cloud_run_v2_job.etl.name
  location = google_cloud_run_v2_job.etl.location
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler_invoker.email}"
}

moved {
  from = google_cloud_scheduler_job.etl_weekly
  to   = google_cloud_scheduler_job.etl_daily
}

resource "google_cloud_scheduler_job" "etl_daily" {
  name      = "${var.job_name}-schedule"
  region    = var.scheduler_region
  schedule  = var.schedule
  time_zone = var.schedule_timezone

  http_target {
    http_method = "POST"
    uri         = "https://${var.gcp_region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.gcp_project}/jobs/${google_cloud_run_v2_job.etl.name}:run"

    oauth_token {
      service_account_email = google_service_account.scheduler_invoker.email
    }
  }

  depends_on = [google_project_service.apis]
}
