output "instance_id" {
  description = "EC2 instance id for the single origin host."
  value       = aws_instance.app_host.id
}

output "public_ip" {
  description = "Elastic IP address attached to the origin host."
  value       = aws_eip.app_host.public_ip
}

output "elastic_ip_allocation_id" {
  description = "Elastic IP allocation id for the origin host."
  value       = aws_eip.app_host.id
}

output "origin_record_fqdn" {
  description = "Route53 fqdn used by CloudFront as the custom origin hostname."
  value       = trimsuffix(aws_route53_record.origin.fqdn, ".")
}
