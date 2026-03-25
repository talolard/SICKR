variable "name_prefix" {
  description = "Shared environment resource prefix."
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet ids used by the ALB and the Fargate tasks."
  type        = list(string)
}

variable "vpc_id" {
  description = "VPC id shared by the ALB target groups and ECS services."
  type        = string
}

variable "alb_security_group_id" {
  description = "Security group id attached to the public ALB."
  type        = string
}

variable "ui_service_security_group_id" {
  description = "Security group id attached to the UI ECS service."
  type        = string
}

variable "backend_service_security_group_id" {
  description = "Security group id attached to the backend ECS service."
  type        = string
}

variable "backend_app_secret_arn" {
  description = "Secrets Manager ARN for backend-only application secrets."
  type        = string
}

variable "model_provider_secret_arn" {
  description = "Secrets Manager ARN for model-provider credentials."
  type        = string
}

variable "observability_secret_arn" {
  description = "Secrets Manager ARN for observability credentials."
  type        = string
}

variable "database_secret_arn" {
  description = "Secrets Manager ARN for the runtime DATABASE_URL."
  type        = string
}

variable "private_artifacts_bucket_name" {
  description = "Private S3 bucket used for attachments and generated artifacts."
  type        = string
}

variable "product_image_base_url" {
  description = "Stable same-host public base URL for deployed product images."
  type        = string
}

variable "region" {
  description = "Primary AWS region for logs and service metadata."
  type        = string
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
}

variable "ui_container_port" {
  description = "Container port exposed by the UI service."
  type        = number
}

variable "backend_container_port" {
  description = "Container port exposed by the backend service."
  type        = number
}

variable "ui_task_cpu" {
  description = "CPU units reserved for the UI Fargate task."
  type        = number
}

variable "ui_task_memory" {
  description = "Memory in MiB reserved for the UI Fargate task."
  type        = number
}

variable "backend_task_cpu" {
  description = "CPU units reserved for the backend Fargate task."
  type        = number
}

variable "backend_task_memory" {
  description = "Memory in MiB reserved for the backend Fargate task."
  type        = number
}

variable "initial_desired_count" {
  description = "Initial ECS service desired count before the first image rollout."
  type        = number
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days for ECS task logs."
  type        = number
}

variable "common_tags" {
  description = "Provider-level deployment tags to merge with resource-local tags."
  type        = map(string)
}
