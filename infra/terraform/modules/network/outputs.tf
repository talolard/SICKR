output "vpc_id" {
  description = "VPC id for the deployment environment."
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Ordered public subnet ids for the ALB and public-IP Fargate tasks."
  value       = [for key in sort(keys(aws_subnet.public)) : aws_subnet.public[key].id]
}

output "database_subnet_ids" {
  description = "Ordered private subnet ids reserved for Aurora."
  value       = [for key in sort(keys(aws_subnet.database)) : aws_subnet.database[key].id]
}

output "alb_security_group_id" {
  description = "Security group id for the internet-facing application load balancer."
  value       = aws_security_group.alb.id
}

output "ui_service_security_group_id" {
  description = "Security group id for the UI ECS service."
  value       = aws_security_group.ui_service.id
}

output "backend_service_security_group_id" {
  description = "Security group id for the backend ECS service."
  value       = aws_security_group.backend_service.id
}

output "database_security_group_id" {
  description = "Security group id for Aurora ingress from the backend ECS service."
  value       = aws_security_group.database.id
}
