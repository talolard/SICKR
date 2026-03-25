variable "product_image_bucket_name" {
  description = "Globally unique bucket name for the public product-image objects."
  type        = string
}

variable "private_artifacts_bucket_name" {
  description = "Globally unique bucket name for private attachments and generated artifacts."
  type        = string
}

variable "common_tags" {
  description = "Provider-level deployment tags to merge with resource-local tags."
  type        = map(string)
}
