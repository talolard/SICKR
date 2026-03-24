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

output "origin_hostname" {
  description = "Origin hostname reserved for the app host."
  value       = local.origin_hostname_trimmed
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
  value       = local.product_image_bucket_name
}

output "private_artifacts_bucket_name" {
  description = "Planned private artifacts bucket name reserved by the foundation."
  value       = local.private_artifacts_bucket_name
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

output "runtime_role_arn" {
  description = "EC2 runtime role ARN."
  value       = aws_iam_role.runtime.arn
}

output "runtime_instance_profile_name" {
  description = "EC2 runtime instance profile name."
  value       = aws_iam_instance_profile.runtime.name
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
