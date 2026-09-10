resource "google_cloud_run_v2_job" "etl" {
  name                = var.job_name
  location            = var.gcp_region
  deletion_protection = false

  template {
    template {
      service_account = google_service_account.etl_runtime.email
      max_retries      = 1
      timeout          = "900s" # scraping + geocoding a couple hundred addresses

      containers {
        # Placeholder on first apply — the Cloud Build trigger repoints this
        # at the freshly built image on every push to `deploy_branch`.
        image = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project}/hirudo/etl:latest"

        dynamic "env" {
          for_each = toset(local.etl_secrets)
          content {
            name = upper(replace(env.value, "-", "_"))
            value_source {
              secret_key_ref {
                secret  = google_secret_manager_secret.etl[env.value].secret_id
                version = "latest"
              }
            }
          }
        }
      }
    }
  }

  lifecycle {
    # Cloud Build owns the image tag after the first deploy; don't fight it.
    ignore_changes = [template[0].template[0].containers[0].image]
  }

  depends_on = [google_project_service.apis]
}
