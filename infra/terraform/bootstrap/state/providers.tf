variable "aws_account_id" {
  description = "AWS account id allowed for the bootstrap state root."
  type        = string
  default     = "046673074482"
}

variable "region" {
  description = "Primary region for the Terraform state bucket."
  type        = string
  default     = "eu-central-1"
}

variable "bucket_name" {
  description = "State bucket name."
  type        = string
  default     = "tal-maria-ikea-terraform-state-046673074482-eu-central-1"
}

locals {
  default_tags = {
    Project     = "tal-maria-ikea"
    Service     = "ikea-agent"
    Environment = "dev"
    ManagedBy   = "terraform"
    Repository  = "talolard/SICKR"
    Owner       = "tal"
  }
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.aws_account_id]

  default_tags {
    tags = local.default_tags
  }
}
