output "github_connection_stage" {
  description = "Status of the GitHub connection. Should read COMPLETE — if not, github_connection_action_uri names a leftover manual step."
  value       = try(google_cloudbuildv2_connection.github.installation_state[0].stage, null)
}

output "github_connection_action_uri" {
  description = "Only relevant if github_connection_stage isn't COMPLETE — a link to finish authorizing in the browser."
  value       = try(google_cloudbuildv2_connection.github.installation_state[0].action_uri, null)
}

output "artifact_registry_repo" {
  value = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project}/${google_artifact_registry_repository.hirudo.repository_id}"
}

output "cloud_run_job_name" {
  value = google_cloud_run_v2_job.etl.name
}
