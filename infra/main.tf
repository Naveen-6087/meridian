terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# ---------------------------------------------------------------------------
# Compute: one Always-Free e2-micro VM
# ---------------------------------------------------------------------------
resource "google_compute_instance" "baseline_vm" {
  name         = "p14-baseline-vm"
  machine_type = "e2-micro"
  zone         = var.zone

  labels = {
    project     = "p14-drift-ranking"
    owner       = "student"
    environment = "experiment"
  }

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
      size  = 10
      type  = "pd-standard"
    }
  }

  network_interface {
    network = google_compute_network.baseline_net.id
    subnetwork = google_compute_subnetwork.baseline_subnet.id
    access_config {} # ephemeral public IP
  }

  shielded_instance_config {
    enable_secure_boot = true
  }
}

# ---------------------------------------------------------------------------
# Network: dedicated VPC + subnet + firewall rule (baseline: SSH only)
# ---------------------------------------------------------------------------
resource "google_compute_network" "baseline_net" {
  name                    = "p14-baseline-net"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "baseline_subnet" {
  name          = "p14-baseline-subnet"
  ip_cidr_range = "10.10.0.0/24"
  region        = var.region
  network       = google_compute_network.baseline_net.id
}

resource "google_compute_firewall" "allow_ssh" {
  name    = "p14-allow-ssh"
  network = google_compute_network.baseline_net.id

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  # Baseline: restricted to a single administrative CIDR, not 0.0.0.0/0.
  source_ranges = ["203.0.113.0/24"]

  target_tags = ["p14-baseline"]
}

# ---------------------------------------------------------------------------
# Storage: one small regional bucket, private by default
# ---------------------------------------------------------------------------
resource "google_storage_bucket" "baseline_bucket" {
  name                        = "${var.project_id}-p14-baseline-bucket"
  location                    = "US-CENTRAL1"
  storage_class               = "STANDARD"
  force_destroy               = true
  uniform_bucket_level_access = true

  labels = {
    project     = "p14-drift-ranking"
    owner       = "student"
    environment = "experiment"
  }

  versioning {
    enabled = false
  }
}

# ---------------------------------------------------------------------------
# Identity: one application service account with a narrow, named role
# ---------------------------------------------------------------------------
resource "google_service_account" "app_sa" {
  account_id   = "p14-app-sa"
  display_name = "P14 application service account"
}

resource "google_project_iam_member" "app_sa_binding" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.app_sa.email}"
}
