module "edge" {
  source = "../../modules/edge"

  providers = {
    aws           = aws
    aws.us_east_1 = aws.us_east_1
  }

  name_prefix                               = local.name_prefix
  hosted_zone_id                            = data.aws_route53_zone.public.zone_id
  public_hostname                           = local.public_hostname_trimmed
  app_origin_domain_name                    = module.runtime.alb_dns_name
  app_origin_port                           = 80
  product_image_bucket_regional_domain_name = module.storage.product_image_bucket_regional_domain_name
  cloudfront_price_class                    = var.cloudfront_price_class
  app_origin_read_timeout_seconds           = var.cloudfront_app_origin_read_timeout_seconds
  origin_keepalive_timeout_seconds          = var.cloudfront_origin_keepalive_timeout_seconds
  common_tags                               = local.default_tags
}
