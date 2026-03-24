locals {
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.aws_account_id]

  default_tags {
    tags = local.default_tags
  }
}

provider "aws" {
  alias               = "us_east_1"
  region              = var.cloudfront_certificate_region
  allowed_account_ids = [var.aws_account_id]

  default_tags {
    tags = local.default_tags
  }
}
