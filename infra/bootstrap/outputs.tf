output "resource_group_name" { value = azurerm_resource_group.project.name }
output "state_storage_account" { value = azurerm_storage_account.state.name }
output "deploy_client_id" { value = azurerm_user_assigned_identity.deploy.client_id }
output "runtime_identity_id" { value = azurerm_user_assigned_identity.runtime.id }
