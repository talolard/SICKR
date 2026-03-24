output "product_image_bucket_id" {
  description = "Product-image bucket id."
  value       = aws_s3_bucket.product_images.id
}

output "product_image_bucket_arn" {
  description = "Product-image bucket ARN."
  value       = aws_s3_bucket.product_images.arn
}

output "product_image_bucket_regional_domain_name" {
  description = "Regional domain name used by CloudFront for the product-image bucket origin."
  value       = aws_s3_bucket.product_images.bucket_regional_domain_name
}

output "private_artifacts_bucket_id" {
  description = "Private artifacts bucket id."
  value       = aws_s3_bucket.private_artifacts.id
}

output "private_artifacts_bucket_arn" {
  description = "Private artifacts bucket ARN."
  value       = aws_s3_bucket.private_artifacts.arn
}
