data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_route53_zone" "public" {
  name         = var.hosted_zone_name
  private_zone = false
}

check "account_guardrail" {
  assert {
    condition     = data.aws_caller_identity.current.account_id == var.aws_account_id
    error_message = "Terraform is authenticated against the wrong AWS account."
  }
}

check "region_guardrail" {
  assert {
    condition     = data.aws_region.current.region == var.region
    error_message = "Terraform is authenticated against the wrong primary region."
  }
}

check "availability_zone_guardrail" {
  assert {
    condition = length(data.aws_availability_zones.available.names) >= max(
      length(var.public_subnet_cidrs),
      length(var.database_subnet_cidrs),
    )
    error_message = "Not enough availability zones are available for the configured subnet topology."
  }
}
