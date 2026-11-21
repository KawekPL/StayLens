terraform {
  required_version = "= 1.16.5"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "= 4.81.0" }
  }
  backend "azurerm" {}
}
provider "azurerm" {
  features {}
  subscription_id                 = var.subscription_id
  resource_provider_registrations = "none"
}

variable "subscription_id" { type = string }
variable "resource_group_name" { type = string }
variable "environment_id" { type = string }
variable "runtime_identity_id" { type = string }
variable "acr_login_server" { type = string }
variable "image_digest" {
  type = string
  validation {
    condition     = can(regex("^sha256:[0-9a-f]{64}$", var.image_digest))
    error_message = "Deploy an immutable image digest, never a mutable tag."
  }
}

resource "azurerm_container_app" "staylens" {
  name                         = "staylens"
  resource_group_name          = var.resource_group_name
  container_app_environment_id = var.environment_id
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"
  tags                         = { project = "StayLens", environment = "student" }
  identity {
    type         = "UserAssigned"
    identity_ids = [var.runtime_identity_id]
  }
  registry {
    server   = var.acr_login_server
    identity = var.runtime_identity_id
  }
  ingress {
    external_enabled           = true
    target_port                = 8080
    transport                  = "http"
    allow_insecure_connections = false
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
  template {
    min_replicas = 0
    max_replicas = 1
    http_scale_rule {
      name                = "http-scaler"
      concurrent_requests = "10"
    }
    container {
      name   = "staylens"
      image  = "${var.acr_login_server}/staylens@${var.image_digest}"
      cpu    = 0.5
      memory = "1Gi"
      startup_probe {
        transport               = "HTTP"
        port                    = 8080
        path                    = "/health"
        interval_seconds        = 5
        timeout                 = 3
        failure_count_threshold = 24
      }
      readiness_probe {
        transport               = "HTTP"
        port                    = 8080
        path                    = "/health"
        interval_seconds        = 10
        timeout                 = 3
        failure_count_threshold = 3
      }
      liveness_probe {
        transport               = "HTTP"
        port                    = 8080
        path                    = "/health"
        interval_seconds        = 30
        timeout                 = 3
        failure_count_threshold = 3
      }
    }
  }
  lifecycle {
    # In Single mode Azure routes all traffic to the active revision, and can
    # omit traffic_weight on GET (also observed on the existing shared setup).
    # Keep probes/scaling/image tracked; ignore only this redundant API field.
    ignore_changes = [ingress[0].traffic_weight]
  }
}

output "url" { value = "https://${azurerm_container_app.staylens.ingress[0].fqdn}" }
output "image_digest" { value = var.image_digest }
