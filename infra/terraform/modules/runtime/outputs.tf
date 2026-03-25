output "alb_arn" {
  description = "ARN of the public application load balancer."
  value       = aws_lb.main.arn
}

output "alb_dns_name" {
  description = "DNS name of the public ALB used as the CloudFront app origin."
  value       = aws_lb.main.dns_name
}

output "cluster_arn" {
  description = "ARN of the ECS cluster."
  value       = aws_ecs_cluster.main.arn
}

output "cluster_name" {
  description = "Name of the ECS cluster."
  value       = aws_ecs_cluster.main.name
}

output "backend_service_name" {
  description = "Name of the backend ECS service."
  value       = aws_ecs_service.backend.name
}

output "ui_service_name" {
  description = "Name of the UI ECS service."
  value       = aws_ecs_service.ui.name
}

output "backend_task_definition_family" {
  description = "Task-definition family name for backend releases."
  value       = aws_ecs_task_definition.backend.family
}

output "ui_task_definition_family" {
  description = "Task-definition family name for UI releases."
  value       = aws_ecs_task_definition.ui.family
}
