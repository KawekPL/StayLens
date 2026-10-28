output "url" { value = "https://${azurerm_container_app.staylens.ingress[0].fqdn}" }
output "image_digest" { value = var.image_digest }
