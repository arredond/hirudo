# PAT for the already-installed Cloud Build GitHub App (see terraform/README.md).
# Terraform only creates the empty container — set the value with:
#   gcloud secrets versions add github-token --data-file=-
resource "google_secret_manager_secret" "github_token" {
  secret_id = "github-token"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

# The connection resource reads the PAT as the Cloud Build Service Agent,
# a Google-managed identity auto-provisioned once cloudbuild.googleapis.com
# is enabled — not to be confused with the cloudbuild.gserviceaccount.com
# build-runner SA used elsewhere in this config.
resource "google_secret_manager_secret_iam_member" "cloudbuild_agent_reads_token" {
  secret_id = google_secret_manager_secret.github_token.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:service-${data.google_project.this.number}@gcp-sa-cloudbuild.iam.gserviceaccount.com"

  depends_on = [google_project_service.apis]
}

# 2nd-gen GitHub connection, fully non-interactive: it points at the GitHub
# App installation + PAT you set up per terraform/README.md, so `apply`
# shouldn't need any follow-up browser step.
resource "google_cloudbuildv2_connection" "github" {
  location = var.gcp_region
  name     = "${var.github_repo}-github"

  github_config {
    app_installation_id = var.github_app_installation_id
    authorizer_credential {
      oauth_token_secret_version = "${google_secret_manager_secret.github_token.id}/versions/latest"
    }
  }

  depends_on = [google_secret_manager_secret_iam_member.cloudbuild_agent_reads_token]
}

resource "google_cloudbuildv2_repository" "hirudo" {
  location          = var.gcp_region
  name              = var.github_repo
  parent_connection = google_cloudbuildv2_connection.github.name
  remote_uri        = "https://github.com/${var.github_owner}/${var.github_repo}.git"
}

resource "google_cloudbuild_trigger" "deploy_etl" {
  location = var.gcp_region
  name     = "${var.job_name}-deploy"

  repository_event_config {
    repository = google_cloudbuildv2_repository.hirudo.id
    push {
      branch = "^${var.deploy_branch}$"
    }
  }

  filename = "cloudbuild.yaml"

  substitutions = {
    _REGION   = var.gcp_region
    _REPO     = google_artifact_registry_repository.hirudo.repository_id
    _JOB_NAME = google_cloud_run_v2_job.etl.name
    _SA_EMAIL = google_service_account.etl_runtime.email
  }

  depends_on = [google_project_service.apis]
}
