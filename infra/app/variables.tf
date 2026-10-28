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
