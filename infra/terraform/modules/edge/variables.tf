variable "name_prefix" {
  description = "Shared environment resource prefix."
  type        = string
}

variable "hosted_zone_id" {
  description = "Route53 hosted zone id for talperry.com."
  type        = string
}

variable "public_hostname" {
  description = "Public app hostname aliased to the CloudFront distribution."
  type        = string
}

variable "app_origin_domain_name" {
  description = "Stable origin hostname that resolves to the EC2 Elastic IP."
  type        = string
}

variable "product_image_bucket_regional_domain_name" {
  description = "Regional S3 domain name used as the CloudFront product-image origin."
  type        = string
}

variable "cloudfront_price_class" {
  description = "CloudFront price class for the public edge."
  type        = string
}

variable "default_app_origin_read_timeout_seconds" {
  description = "Read timeout for the default app-origin behavior."
  type        = number
}

variable "ag_ui_origin_read_timeout_seconds" {
  description = "Read timeout for the AG-UI origin behavior."
  type        = number
}

variable "origin_keepalive_timeout_seconds" {
  description = "Keepalive timeout used by the CloudFront custom origins."
  type        = number
}

variable "common_tags" {
  description = "Provider-level deployment tags to merge with resource-local tags."
  type        = map(string)
}
