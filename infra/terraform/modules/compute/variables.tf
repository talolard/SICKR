variable "name_prefix" {
  description = "Shared environment resource prefix."
  type        = string
}

variable "subnet_id" {
  description = "Public subnet id for the single origin EC2 host."
  type        = string
}

variable "security_group_ids" {
  description = "Security groups attached to the origin EC2 host."
  type        = list(string)
}

variable "instance_profile_name" {
  description = "IAM instance profile attached to the EC2 host."
  type        = string
}

variable "hosted_zone_id" {
  description = "Route53 hosted zone id where the origin hostname record is managed."
  type        = string
}

variable "origin_hostname" {
  description = "Stable DNS name reserved for CloudFront to reach the origin host."
  type        = string
}

variable "ami_ssm_parameter_name" {
  description = "SSM public parameter that resolves to the Amazon Linux AMI id."
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type for the single origin host."
  type        = string
}

variable "root_volume_size_gib" {
  description = "Root volume size in GiB for the single origin host."
  type        = number
}

variable "artifact_root_dir" {
  description = "Writable host path reserved for private runtime artifacts."
  type        = string
}

variable "ssh_key_name" {
  description = "Optional EC2 key pair for fallback SSH access."
  type        = string
  default     = null
}

variable "common_tags" {
  description = "Provider-level deployment tags to merge with resource-local tags."
  type        = map(string)
}
