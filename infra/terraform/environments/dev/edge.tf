module "edge" {
  source = "../../modules/edge"

  providers = {
    aws           = aws
    aws.us_east_1 = aws.us_east_1
  }

  name_prefix                               = local.name_prefix
  hosted_zone_id                            = data.aws_route53_zone.public.zone_id
  public_hostname                           = local.public_hostname_trimmed
  app_origin_domain_name                    = module.compute.origin_record_fqdn
  ui_origin_port                            = var.app_ui_origin_port
  backend_origin_port                       = var.app_backend_origin_port
  product_image_bucket_regional_domain_name = module.storage.product_image_bucket_regional_domain_name
  cloudfront_price_class                    = var.cloudfront_price_class
  default_app_origin_read_timeout_seconds   = var.cloudfront_default_origin_read_timeout_seconds
  ag_ui_origin_read_timeout_seconds         = var.cloudfront_ag_ui_origin_read_timeout_seconds
  origin_keepalive_timeout_seconds          = var.cloudfront_origin_keepalive_timeout_seconds
  common_tags                               = local.default_tags
}
