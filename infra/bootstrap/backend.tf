terraform {
  backend "local" {
    path = "../../.local/staylens-bootstrap.tfstate"
  }
}
