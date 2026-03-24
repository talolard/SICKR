locals {
  base_tags = {
    Service     = var.service_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Project     = "deployproject"
    Repository  = "talolard/SICKR"
  }
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.aws_account_id]

  default_tags {
    tags = merge(local.base_tags, var.extra_tags)
  }
}

provider "aws" {
  alias               = "us_east_1"
  region              = var.cloudfront_certificate_region
  allowed_account_ids = [var.aws_account_id]

  default_tags {
    tags = merge(local.base_tags, var.extra_tags)
  }
}
