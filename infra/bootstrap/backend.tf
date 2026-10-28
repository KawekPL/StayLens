terraform {
  backend "azurerm" {
    storage_account_name = "stlens14055600"
    container_name       = "tfstate-bootstrap"
    key                  = "staylens.tfstate"
    use_azuread_auth     = true
  }
}
