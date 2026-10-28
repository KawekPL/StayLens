variable "subscription_id" {
  type = string
}
variable "operator_object_id" {
  type = string
}
variable "suffix" {
  type    = string
  default = "14055600"
}
variable "location" {
  type    = string
  default = "polandcentral"
}
variable "github_repository" {
  type    = string
  default = "KawekPL/StayLens"
}
variable "shared_acr_id" {
  type = string
}
variable "shared_environment_id" {
  type = string
}
variable "monthly_budget_eur" {
  type    = number
  default = 8
  validation {
    condition     = var.monthly_budget_eur > 0 && var.monthly_budget_eur <= 8
    error_message = "Budget guardrail: at most 8 EUR (below the approved 10 USD at the checked exchange rate)."
  }
}
