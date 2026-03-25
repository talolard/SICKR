module "runtime" {
  source = "../../modules/runtime"

  name_prefix                       = local.name_prefix
  vpc_id                            = module.network.vpc_id
  public_subnet_ids                 = module.network.public_subnet_ids
  alb_security_group_id             = module.network.alb_security_group_id
  ui_service_security_group_id      = module.network.ui_service_security_group_id
  backend_service_security_group_id = module.network.backend_service_security_group_id
  backend_app_secret_arn            = aws_secretsmanager_secret.runtime["backend_app"].arn
  model_provider_secret_arn         = aws_secretsmanager_secret.runtime["model_providers"].arn
  observability_secret_arn          = aws_secretsmanager_secret.runtime["observability"].arn
  database_secret_arn               = aws_secretsmanager_secret.runtime["database"].arn
  private_artifacts_bucket_name     = module.storage.private_artifacts_bucket_id
  product_image_base_url            = "https://${local.public_hostname_trimmed}/static/product-images"
  region                            = var.region
  environment                       = var.environment
  ui_container_port                 = var.ui_container_port
  backend_container_port            = var.backend_container_port
  ui_task_cpu                       = var.ui_task_cpu
  ui_task_memory                    = var.ui_task_memory
  backend_task_cpu                  = var.backend_task_cpu
  backend_task_memory               = var.backend_task_memory
  initial_desired_count             = var.runtime_initial_desired_count
  log_retention_days                = var.ecs_log_retention_days
  common_tags                       = local.default_tags
}
