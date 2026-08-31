output "vm_name" {
  value = google_compute_instance.baseline_vm.name
}

output "bucket_name" {
  value = google_storage_bucket.baseline_bucket.name
}

output "service_account_email" {
  value = google_service_account.app_sa.email
}

output "firewall_name" {
  value = google_compute_firewall.allow_ssh.name
}
