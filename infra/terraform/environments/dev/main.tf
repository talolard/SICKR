data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

data "aws_route53_zone" "public" {
  name         = var.hosted_zone_name
  private_zone = false
}

locals {
  public_hostname_trimmed = trimsuffix(var.public_hostname, ".")
  origin_hostname_trimmed = trimsuffix(var.origin_hostname, ".")
}

check "account_guardrail" {
  assert {
    condition     = data.aws_caller_identity.current.account_id == var.aws_account_id
    error_message = "Terraform is authenticated against the wrong AWS account."
  }
}

check "region_guardrail" {
  assert {
    condition     = data.aws_region.current.name == var.region
    error_message = "Terraform is authenticated against the wrong primary region."
  }
}
