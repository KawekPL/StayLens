locals {
  tags = { project = "StayLens", environment = "student" }
  roles = {
    deploy_app         = { principal = azurerm_user_assigned_identity.deploy.principal_id, role = "Container Apps Contributor", scope = azurerm_resource_group.project.id }
    deploy_read        = { principal = azurerm_user_assigned_identity.deploy.principal_id, role = "Reader", scope = azurerm_resource_group.project.id }
    deploy_join        = { principal = azurerm_user_assigned_identity.deploy.principal_id, role = "Container Apps Contributor", scope = var.shared_environment_id }
    deploy_identity    = { principal = azurerm_user_assigned_identity.deploy.principal_id, role = "Managed Identity Operator", scope = azurerm_user_assigned_identity.runtime.id }
    deploy_push        = { principal = azurerm_user_assigned_identity.deploy.principal_id, role = "AcrPush", scope = var.shared_acr_id }
    deploy_state       = { principal = azurerm_user_assigned_identity.deploy.principal_id, role = "Storage Blob Data Contributor", scope = azurerm_storage_container.state["tfstate-app"].resource_manager_id }
    runtime_pull       = { principal = azurerm_user_assigned_identity.runtime.principal_id, role = "AcrPull", scope = var.shared_acr_id }
    operator_bootstrap = { principal = var.operator_object_id, role = "Storage Blob Data Contributor", scope = azurerm_storage_container.state["tfstate-bootstrap"].resource_manager_id }
    operator_app       = { principal = var.operator_object_id, role = "Storage Blob Data Contributor", scope = azurerm_storage_container.state["tfstate-app"].resource_manager_id }
  }
}
resource "azurerm_resource_group" "project" {
  name     = "rg-staylens-${var.suffix}"
  location = var.location
  tags     = local.tags
}
resource "azurerm_storage_account" "state" {
  name                            = "stlens${var.suffix}"
  resource_group_name             = azurerm_resource_group.project.name
  location                        = var.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  shared_access_key_enabled       = false
  allow_nested_items_to_be_public = false
  tags                            = local.tags
  blob_properties {
    versioning_enabled = true
    delete_retention_policy { days = 7 }
    container_delete_retention_policy { days = 7 }
  }
  lifecycle { prevent_destroy = true }
}
resource "azurerm_storage_container" "state" {
  for_each              = toset(["tfstate-bootstrap", "tfstate-app"])
  name                  = each.key
  storage_account_id    = azurerm_storage_account.state.id
  container_access_type = "private"
}
resource "azurerm_user_assigned_identity" "runtime" {
  name                = "id-staylens-runtime-${var.suffix}"
  resource_group_name = azurerm_resource_group.project.name
  location            = var.location
  tags                = local.tags
}
resource "azurerm_user_assigned_identity" "deploy" {
  name                = "id-staylens-deploy-${var.suffix}"
  resource_group_name = azurerm_resource_group.project.name
  location            = var.location
  tags                = local.tags
}
resource "azurerm_federated_identity_credential" "github" {
  name                = "github-main"
  resource_group_name = azurerm_resource_group.project.name
  parent_id           = azurerm_user_assigned_identity.deploy.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = "https://token.actions.githubusercontent.com"
  subject             = "repo:${split("/", var.github_repository)[0]}@${var.github_owner_id}/${split("/", var.github_repository)[1]}@${var.github_repository_id}:ref:refs/heads/main"
}
resource "azurerm_role_assignment" "project" {
  for_each             = local.roles
  scope                = each.value.scope
  role_definition_name = each.value.role
  principal_id         = each.value.principal
}
# One conservative budget for the entire subscription, including the shared old infrastructure.
# Azure bills this account in EUR. Alerts are notifications, NOT a spending cutoff.
resource "azurerm_consumption_budget_subscription" "student" {
  name            = "budget-staylens-student-total"
  subscription_id = "/subscriptions/${var.subscription_id}"
  amount          = var.monthly_budget_eur
  time_grain      = "Monthly"
  time_period { start_date = "2026-10-01T00:00:00Z" }
  dynamic "notification" {
    for_each = toset([80, 100])
    content {
      enabled        = true
      threshold      = notification.value
      operator       = "GreaterThanOrEqualTo"
      contact_roles  = ["Owner"]
      threshold_type = "Actual"
    }
  }
}
