output "cluster_identifier" {
  description = "Aurora cluster identifier."
  value       = aws_rds_cluster.main.cluster_identifier
}

output "endpoint" {
  description = "Aurora writer endpoint."
  value       = aws_rds_cluster.main.endpoint
}

output "port" {
  description = "Aurora PostgreSQL listener port."
  value       = aws_rds_cluster.main.port
}

output "master_user_secret_arn" {
  description = "AWS-managed master credential secret ARN for the Aurora cluster."
  value       = aws_rds_cluster.main.master_user_secret[0].secret_arn
}

output "db_subnet_group_name" {
  description = "Aurora DB subnet group name."
  value       = aws_db_subnet_group.main.name
}

output "instance_parameter_group_name" {
  description = "Instance parameter group that enforces the idle session policy."
  value       = aws_db_parameter_group.instance.name
}
