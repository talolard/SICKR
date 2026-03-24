module "compute" {
  source = "../../modules/compute"

  name_prefix            = local.name_prefix
  subnet_id              = module.network.public_subnet_ids[0]
  security_group_ids     = [module.network.app_host_security_group_id]
  instance_profile_name  = aws_iam_instance_profile.runtime.name
  hosted_zone_id         = data.aws_route53_zone.public.zone_id
  origin_hostname        = local.origin_hostname_trimmed
  ami_ssm_parameter_name = var.app_host_ami_ssm_parameter_name
  instance_type          = var.app_host_instance_type
  root_volume_size_gib   = var.app_host_root_volume_size_gib
  artifact_root_dir      = var.app_host_artifact_root_dir
  ssh_key_name           = var.app_host_ssh_key_name
  common_tags            = local.default_tags
}
