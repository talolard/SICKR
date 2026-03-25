output "cloudfront_distribution_id" {
  description = "CloudFront distribution id for the public app edge."
  value       = aws_cloudfront_distribution.main.id
}

output "cloudfront_distribution_arn" {
  description = "CloudFront distribution ARN for downstream bucket-policy wiring."
  value       = aws_cloudfront_distribution.main.arn
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name."
  value       = aws_cloudfront_distribution.main.domain_name
}

output "viewer_certificate_arn" {
  description = "Viewer ACM certificate ARN in us-east-1."
  value       = aws_acm_certificate_validation.viewer.certificate_arn
}
