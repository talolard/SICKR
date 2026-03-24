output "aws_account_id" {
  description = "AWS account id validated by the environment root."
  value       = data.aws_caller_identity.current.account_id
}

output "primary_region" {
  description = "Primary AWS region for the deployment."
  value       = data.aws_region.current.name
}

output "public_hosted_zone_id" {
  description = "Existing Route53 hosted zone id for talperry.com."
  value       = data.aws_route53_zone.public.zone_id
}

output "public_hostname" {
  description = "Primary public hostname reserved for the deployed app."
  value       = local.public_hostname_trimmed
}

output "origin_hostname" {
  description = "Origin hostname reserved for the app host."
  value       = local.origin_hostname_trimmed
}
