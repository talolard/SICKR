variable "name_prefix" {
  description = "Shared environment resource prefix."
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the dedicated deployment VPC."
  type        = string
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for the public subnets."
  type        = list(string)
}

variable "database_subnet_cidrs" {
  description = "CIDR blocks for the private database subnets."
  type        = list(string)
}

variable "availability_zones" {
  description = "Availability zones used by the public and database subnets."
  type        = list(string)

  validation {
    condition = (
      length(var.availability_zones) >= length(var.public_subnet_cidrs) &&
      length(var.availability_zones) >= length(var.database_subnet_cidrs)
    )
    error_message = "The availability zone list must cover both subnet families."
  }
}

variable "common_tags" {
  description = "Provider-level deployment tags to merge with resource-local tags."
  type        = map(string)
}
