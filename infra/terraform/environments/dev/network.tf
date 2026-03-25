module "network" {
  source = "../../modules/network"

  name_prefix             = local.name_prefix
  vpc_cidr                = var.vpc_cidr
  public_subnet_cidrs     = var.public_subnet_cidrs
  database_subnet_cidrs   = var.database_subnet_cidrs
  availability_zones      = local.selected_availability_zones
  app_ui_origin_port      = var.ui_container_port
  app_backend_origin_port = var.backend_container_port
  common_tags             = local.default_tags
}
