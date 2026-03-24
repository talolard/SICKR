output "vpc_id" {
  description = "VPC id for the deployment environment."
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Ordered public subnet ids for the EC2 host and future expansion."
  value       = [for key in sort(keys(aws_subnet.public)) : aws_subnet.public[key].id]
}

output "database_subnet_ids" {
  description = "Ordered private subnet ids reserved for Aurora."
  value       = [for key in sort(keys(aws_subnet.database)) : aws_subnet.database[key].id]
}

output "app_host_security_group_id" {
  description = "Security group id for the internet-facing EC2 origin host."
  value       = aws_security_group.app_host.id
}

output "database_security_group_id" {
  description = "Security group id for Aurora ingress from the EC2 origin host."
  value       = aws_security_group.database.id
}
