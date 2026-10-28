resource "azurerm_container_app" "staylens" {
  name                         = "staylens"
  resource_group_name          = var.resource_group_name
  container_app_environment_id = var.environment_id
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"
  max_inactive_revisions       = 2
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
}
