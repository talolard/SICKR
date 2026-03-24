variable "aws_account_id" {
  description = "AWS account id allowed for this environment."
  type        = string
  default     = "046673074482"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "dev"
}

variable "service_name" {
  description = "Shared Terraform resource prefix for this service."
  type        = string
  default     = "ikea-agent"
}

variable "region" {
  description = "Primary AWS region for app infrastructure."
  type        = string
  default     = "eu-central-1"
}

variable "cloudfront_certificate_region" {
  description = "Region required for CloudFront viewer ACM certificates."
  type        = string
  default     = "us-east-1"
}

variable "hosted_zone_name" {
  description = "Public hosted zone name already present in Route53."
  type        = string
  default     = "talperry.com"
}

variable "public_hostname" {
  description = "Primary public hostname for the deployed app."
  type        = string
  default     = "designagent.talperry.com"
}

variable "origin_hostname" {
  description = "Origin hostname for the EC2-backed application host."
  type        = string
  default     = "origin.designagent.talperry.com"
}

variable "extra_tags" {
  description = "Additional environment tags applied on top of the shared base tags."
  type        = map(string)
  default     = {}
}
