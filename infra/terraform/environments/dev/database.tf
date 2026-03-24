module "database" {
  source = "../../modules/database"

  name_prefix              = local.name_prefix
  subnet_ids               = module.network.database_subnet_ids
  security_group_ids       = [module.network.database_security_group_id]
  database_name            = var.database_name
  master_username          = var.database_master_username
  engine_version           = var.database_engine_version
  parameter_group_family   = local.database_parameter_group_family
  min_capacity             = var.database_min_capacity
  max_capacity             = var.database_max_capacity
  seconds_until_auto_pause = var.database_seconds_until_auto_pause
  common_tags              = local.default_tags
}
