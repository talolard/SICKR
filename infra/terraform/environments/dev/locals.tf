locals {
  public_hostname_trimmed = trimsuffix(var.public_hostname, ".")
  selected_availability_zones = slice(
    data.aws_availability_zones.available.names,
    0,
    max(length(var.public_subnet_cidrs), length(var.database_subnet_cidrs)),
  )

  name_prefix               = "${var.service_name}-${var.environment}"
  github_oidc_provider_url  = "https://token.actions.githubusercontent.com"
  github_oidc_provider_host = "token.actions.githubusercontent.com"
  github_actions_subjects = [
    "repo:${var.github_repository}:ref:refs/heads/${var.release_branch}",
  ]

  product_image_bucket_name     = "${local.name_prefix}-${var.aws_account_id}-product-images"
  private_artifacts_bucket_name = "${local.name_prefix}-${var.aws_account_id}-private-artifacts"

  secret_names = {
    backend_app     = "tal-maria-ikea/${var.environment}/backend-app"
    model_providers = "tal-maria-ikea/${var.environment}/model-providers"
    observability   = "tal-maria-ikea/${var.environment}/observability"
    database        = "tal-maria-ikea/${var.environment}/database"
  }

  release_publish_role_name       = "${local.name_prefix}-release-publish"
  deploy_role_name                = "${local.name_prefix}-deploy"
  terraform_apply_role_name       = "${local.name_prefix}-terraform-apply"
  runtime_secret_arns             = values(aws_secretsmanager_secret.runtime)[*].arn
  ecr_repository_names            = { ui = "${var.service_name}/ui", backend = "${var.service_name}/backend" }
  database_parameter_group_family = "aurora-postgresql${split(".", var.database_engine_version)[0]}"

  default_tags = merge(
    {
      Project     = "tal-maria-ikea"
      Service     = var.service_name
      Environment = var.environment
      ManagedBy   = "terraform"
      Repository  = "talolard/SICKR"
      Owner       = "tal"
    },
    var.extra_tags,
  )

  internal_tags = {
    Component          = "deploy-foundation"
    Role               = "shared"
    DataClassification = "internal"
  }
}
