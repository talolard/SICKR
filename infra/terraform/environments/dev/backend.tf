terraform {
  backend "s3" {
    bucket       = "tal-maria-ikea-terraform-state-046673074482-eu-central-1"
    key          = "deploy/dev/terraform.tfstate"
    region       = "eu-central-1"
    encrypt      = true
    use_lockfile = true
  }
}
