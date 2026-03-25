resource "aws_db_subnet_group" "main" {
  name       = "${var.name_prefix}-database"
  subnet_ids = var.subnet_ids

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-database"
    Component          = "database"
    Role               = "subnet-group"
    DataClassification = "private"
  })
}

resource "aws_db_parameter_group" "instance" {
  name        = "${var.name_prefix}-instance"
  family      = var.parameter_group_family
  description = "Pause-friendly Aurora PostgreSQL instance parameters for ${var.name_prefix}."

  parameter {
    name         = "idle_session_timeout"
    value        = "900000"
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "idle_in_transaction_session_timeout"
    value        = "60000"
    apply_method = "pending-reboot"
  }

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-instance"
    Component          = "database"
    Role               = "instance-parameter-group"
    DataClassification = "private"
  })
}

resource "aws_rds_cluster" "main" {
  cluster_identifier           = "${var.name_prefix}-db"
  engine                       = "aurora-postgresql"
  engine_mode                  = "provisioned"
  engine_version               = var.engine_version
  database_name                = var.database_name
  master_username              = var.master_username
  manage_master_user_password  = true
  db_subnet_group_name         = aws_db_subnet_group.main.name
  vpc_security_group_ids       = var.security_group_ids
  storage_encrypted            = true
  backup_retention_period      = 7
  preferred_backup_window      = "02:00-03:00"
  preferred_maintenance_window = "sun:03:00-sun:04:00"
  copy_tags_to_snapshot        = true
  deletion_protection          = false
  skip_final_snapshot          = true
  delete_automated_backups     = true
  enable_http_endpoint         = false

  serverlessv2_scaling_configuration {
    min_capacity             = var.min_capacity
    max_capacity             = var.max_capacity
    seconds_until_auto_pause = var.seconds_until_auto_pause
  }

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-db"
    Component          = "database"
    Role               = "cluster"
    DataClassification = "private"
  })
}

resource "aws_rds_cluster_instance" "writer" {
  identifier              = "${var.name_prefix}-db-1"
  cluster_identifier      = aws_rds_cluster.main.id
  instance_class          = "db.serverless"
  engine                  = aws_rds_cluster.main.engine
  engine_version          = aws_rds_cluster.main.engine_version
  db_parameter_group_name = aws_db_parameter_group.instance.name
  promotion_tier          = 0

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-db-1"
    Component          = "database"
    Role               = "writer"
    DataClassification = "private"
  })
}
