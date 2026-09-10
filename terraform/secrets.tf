# Only the env vars main.py / utils actually read (see etl/utils/db.py and
# etl/utils/geocode.py). HERE_API_KEY and SUPABASE_API_KEY are unused by the
# ETL as of the run_etl() rewrite, so no secrets are created for them.
locals {
  etl_secrets = [
    "pg-host",
    "pg-database",
    "pg-port",
    "pg-user",
    "pg-password",
    "google-maps-api-key",
  ]
}

resource "google_secret_manager_secret" "etl" {
  for_each  = toset(local.etl_secrets)
  secret_id = each.value

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

# Terraform only creates the secret containers — it does not manage secret
# *values*, so they never end up in state or in this repo. Set them once with:
#   echo -n "<value>" | gcloud secrets versions add <secret-id> --data-file=-

resource "google_secret_manager_secret_iam_member" "etl_runtime_access" {
  for_each  = google_secret_manager_secret.etl
  secret_id = each.value.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.etl_runtime.email}"
}
