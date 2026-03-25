variable "name_prefix" {
  description = "Shared environment resource prefix."
  type        = string
}

variable "subnet_ids" {
  description = "Private subnet ids reserved for the Aurora subnet group."
  type        = list(string)
}

variable "security_group_ids" {
  description = "Security groups attached to the Aurora cluster."
  type        = list(string)
}

variable "database_name" {
  description = "Initial database name created inside the Aurora cluster."
  type        = string
}

variable "master_username" {
  description = "Master username for the Aurora cluster."
  type        = string
}

variable "engine_version" {
  description = "Aurora PostgreSQL engine version pinned for the v1 deployment."
  type        = string
}

variable "parameter_group_family" {
  description = "Aurora PostgreSQL parameter group family that matches the engine major version."
  type        = string
}

variable "min_capacity" {
  description = "Minimum Aurora Serverless v2 capacity in ACUs."
  type        = number
}

variable "max_capacity" {
  description = "Maximum Aurora Serverless v2 capacity in ACUs."
  type        = number
}

variable "seconds_until_auto_pause" {
  description = "Idle timeout before Aurora Serverless v2 attempts to auto-pause."
  type        = number
}

variable "common_tags" {
  description = "Provider-level deployment tags to merge with resource-local tags."
  type        = map(string)
}
