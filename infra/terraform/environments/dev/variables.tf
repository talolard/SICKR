variable "aws_account_id" {
  description = "AWS account id allowed for this environment."
  type        = string
  default     = "046673074482"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "dev"
}

variable "service_name" {
  description = "Shared Terraform resource prefix for this service."
  type        = string
  default     = "ikea-agent"
}

variable "region" {
  description = "Primary AWS region for app infrastructure."
  type        = string
  default     = "eu-central-1"
}

variable "cloudfront_certificate_region" {
  description = "Region required for CloudFront viewer ACM certificates."
  type        = string
  default     = "us-east-1"
}

variable "hosted_zone_name" {
  description = "Public hosted zone name already present in Route53."
  type        = string
  default     = "talperry.com"
}

variable "public_hostname" {
  description = "Primary public hostname for the deployed app."
  type        = string
  default     = "designagent.talperry.com"
}

variable "origin_hostname" {
  description = "Origin hostname for the EC2-backed application host."
  type        = string
  default     = "origin.designagent.talperry.com"
}

variable "github_repository" {
  description = "GitHub repository allowed to assume the release and deploy roles."
  type        = string
  default     = "talolard/SICKR"
}

variable "release_branch" {
  description = "Release branch allowed to publish release artifacts."
  type        = string
  default     = "release"
}

variable "extra_tags" {
  description = "Additional environment tags applied on top of the shared base tags."
  type        = map(string)
  default     = {}
}

variable "vpc_cidr" {
  description = "CIDR block for the dedicated deployment VPC."
  type        = string
  default     = "10.42.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for the public subnets used by the app host."
  type        = list(string)
  default     = ["10.42.0.0/24", "10.42.1.0/24"]
}

variable "database_subnet_cidrs" {
  description = "CIDR blocks for the private database subnets used by Aurora."
  type        = list(string)
  default     = ["10.42.10.0/24", "10.42.11.0/24"]
}

variable "app_host_ami_ssm_parameter_name" {
  description = "SSM parameter used to resolve the current Amazon Linux 2023 x86_64 AMI."
  type        = string
  default     = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-6.1-x86_64"
}

variable "app_host_instance_type" {
  description = "EC2 instance type for the single public origin host."
  type        = string
  default     = "t3.small"
}

variable "app_host_root_volume_size_gib" {
  description = "Root volume size for the app host."
  type        = number
  default     = 20
}

variable "app_host_artifact_root_dir" {
  description = "Writable host path reserved for private runtime artifacts."
  type        = string
  default     = "/var/lib/ikea-agent/artifacts"
}

variable "app_host_ssh_key_name" {
  description = "Optional EC2 key pair name for fallback SSH access."
  type        = string
  default     = null
}

variable "database_name" {
  description = "Initial database name created in Aurora."
  type        = string
  default     = "ikea_agent"
}

variable "database_master_username" {
  description = "Master username for the Aurora cluster."
  type        = string
  default     = "ikea_agent_admin"
}

variable "database_engine_version" {
  description = "Pinned Aurora PostgreSQL engine version for the initial deployment."
  type        = string
  default     = "17.7"
}

variable "database_min_capacity" {
  description = "Minimum Aurora Serverless v2 capacity in ACUs."
  type        = number
  default     = 0
}

variable "database_max_capacity" {
  description = "Maximum Aurora Serverless v2 capacity in ACUs."
  type        = number
  default     = 2
}

variable "database_seconds_until_auto_pause" {
  description = "Idle duration before Aurora Serverless v2 auto-pauses."
  type        = number
  default     = 900
}

variable "cloudfront_price_class" {
  description = "CloudFront price class for the single public edge distribution."
  type        = string
  default     = "PriceClass_100"
}

variable "cloudfront_default_origin_read_timeout_seconds" {
  description = "CloudFront origin read timeout for the default app behavior."
  type        = number
  default     = 30
}

variable "cloudfront_ag_ui_origin_read_timeout_seconds" {
  description = "CloudFront origin read timeout for the AG-UI streaming behavior."
  type        = number
  default     = 120
}

variable "cloudfront_origin_keepalive_timeout_seconds" {
  description = "CloudFront keepalive timeout for the custom origins."
  type        = number
  default     = 60
}
