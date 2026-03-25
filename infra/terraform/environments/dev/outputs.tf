output "aws_account_id" {
  description = "AWS account id validated by the environment root."
  value       = data.aws_caller_identity.current.account_id
}

output "primary_region" {
  description = "Primary AWS region for the deployment."
  value       = data.aws_region.current.region
}

output "public_hosted_zone_id" {
  description = "Existing Route53 hosted zone id for talperry.com."
  value       = data.aws_route53_zone.public.zone_id
}

output "public_hostname" {
  description = "Primary public hostname reserved for the deployed app."
  value       = local.public_hostname_trimmed
}

output "github_oidc_provider_arn" {
  description = "OIDC provider ARN for GitHub Actions federation."
  value       = aws_iam_openid_connect_provider.github.arn
}

output "ui_ecr_repository_name" {
  description = "Name of the UI ECR repository."
  value       = aws_ecr_repository.service["ui"].name
}

output "ui_ecr_repository_uri" {
  description = "URI of the UI ECR repository."
  value       = aws_ecr_repository.service["ui"].repository_url
}

output "backend_ecr_repository_name" {
  description = "Name of the backend ECR repository."
  value       = aws_ecr_repository.service["backend"].name
}

output "backend_ecr_repository_uri" {
  description = "URI of the backend ECR repository."
  value       = aws_ecr_repository.service["backend"].repository_url
}

output "product_image_bucket_name" {
  description = "Planned product image bucket name reserved by the foundation."
  value       = module.storage.product_image_bucket_id
}

output "private_artifacts_bucket_name" {
  description = "Planned private artifacts bucket name reserved by the foundation."
  value       = module.storage.private_artifacts_bucket_id
}

output "backend_app_secret_arn" {
  description = "ARN of the backend-app secret container."
  value       = aws_secretsmanager_secret.runtime["backend_app"].arn
}

output "model_provider_secret_arn" {
  description = "ARN of the model-provider secret container."
  value       = aws_secretsmanager_secret.runtime["model_providers"].arn
}

output "observability_secret_arn" {
  description = "ARN of the observability secret container."
  value       = aws_secretsmanager_secret.runtime["observability"].arn
}

output "database_secret_arn" {
  description = "ARN of the database secret container."
  value       = aws_secretsmanager_secret.runtime["database"].arn
}

output "backend_app_secret_name" {
  description = "Name of the backend-app secret container."
  value       = aws_secretsmanager_secret.runtime["backend_app"].name
}

output "model_provider_secret_name" {
  description = "Name of the model-provider secret container."
  value       = aws_secretsmanager_secret.runtime["model_providers"].name
}

output "observability_secret_name" {
  description = "Name of the observability secret container."
  value       = aws_secretsmanager_secret.runtime["observability"].name
}

output "database_secret_name" {
  description = "Name of the database secret container."
  value       = aws_secretsmanager_secret.runtime["database"].name
}

output "release_publish_role_arn" {
  description = "GitHub Actions role ARN for release image publication."
  value       = aws_iam_role.release_publish.arn
}

output "deploy_role_arn" {
  description = "GitHub Actions role ARN for later deploy automation."
  value       = aws_iam_role.deploy.arn
}

output "terraform_apply_role_arn" {
  description = "Terraform apply role ARN for human or tightly controlled automation."
  value       = aws_iam_role.terraform_apply.arn
}

output "vpc_id" {
  description = "Deployment VPC id."
  value       = module.network.vpc_id
}

output "selected_availability_zones" {
  description = "Availability zones used by the deployment subnets."
  value       = local.selected_availability_zones
}

output "product_image_bucket_arn" {
  description = "ARN of the product-image bucket."
  value       = module.storage.product_image_bucket_arn
}

output "private_artifacts_bucket_arn" {
  description = "ARN of the private artifacts bucket."
  value       = module.storage.private_artifacts_bucket_arn
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster."
  value       = module.runtime.cluster_name
}

output "ecs_backend_service_name" {
  description = "Name of the backend ECS service."
  value       = module.runtime.backend_service_name
}

output "ecs_ui_service_name" {
  description = "Name of the UI ECS service."
  value       = module.runtime.ui_service_name
}

output "app_alb_dns_name" {
  description = "DNS name of the public ALB used as the CloudFront app origin."
  value       = module.runtime.alb_dns_name
}

output "database_cluster_identifier" {
  description = "Aurora cluster identifier."
  value       = module.database.cluster_identifier
}

output "database_endpoint" {
  description = "Aurora writer endpoint."
  value       = module.database.endpoint
}

output "database_port" {
  description = "Aurora PostgreSQL listener port."
  value       = module.database.port
}

output "database_master_secret_arn" {
  description = "AWS-managed secret ARN for the Aurora master user."
  value       = module.database.master_user_secret_arn
}

output "database_instance_parameter_group_name" {
  description = "Instance parameter group enforcing idle session timeouts."
  value       = module.database.instance_parameter_group_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution id for the public app edge."
  value       = module.edge.cloudfront_distribution_id
}

output "cloudfront_distribution_arn" {
  description = "CloudFront distribution ARN for the public app edge."
  value       = module.edge.cloudfront_distribution_arn
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name."
  value       = module.edge.cloudfront_domain_name
}

output "viewer_certificate_arn" {
  description = "Viewer ACM certificate ARN in us-east-1."
  value       = module.edge.viewer_certificate_arn
}
