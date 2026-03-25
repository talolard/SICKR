resource "aws_cloudfront_cache_policy" "dynamic_disabled" {
  name        = "${var.name_prefix}-dynamic-disabled"
  comment     = "Disable caching for dynamic application and AG-UI traffic."
  default_ttl = 0
  max_ttl     = 0
  min_ttl     = 0

  parameters_in_cache_key_and_forwarded_to_origin {
    enable_accept_encoding_brotli = false
    enable_accept_encoding_gzip   = false

    cookies_config {
      cookie_behavior = "none"
    }

    headers_config {
      header_behavior = "none"
    }

    query_strings_config {
      query_string_behavior = "none"
    }
  }
}

resource "aws_cloudfront_cache_policy" "product_images" {
  name        = "${var.name_prefix}-product-images"
  comment     = "Immutable caching for CloudFront-backed product images."
  default_ttl = 604800
  max_ttl     = 31536000
  min_ttl     = 86400

  parameters_in_cache_key_and_forwarded_to_origin {
    enable_accept_encoding_brotli = true
    enable_accept_encoding_gzip   = true

    cookies_config {
      cookie_behavior = "none"
    }

    headers_config {
      header_behavior = "none"
    }

    query_strings_config {
      query_string_behavior = "none"
    }
  }
}

resource "aws_cloudfront_origin_request_policy" "dynamic_all_viewer" {
  name    = "${var.name_prefix}-dynamic-all-viewer"
  comment = "Preserve viewer request context for Next.js SSR/API traffic and AG-UI."

  cookies_config {
    cookie_behavior = "all"
  }

  headers_config {
    header_behavior = "allViewer"
  }

  query_strings_config {
    query_string_behavior = "all"
  }
}

resource "aws_cloudfront_origin_access_control" "product_images" {
  name                              = "${var.name_prefix}-product-images"
  description                       = "SigV4 access from CloudFront to the private product-image bucket."
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_acm_certificate" "viewer" {
  provider          = aws.us_east_1
  domain_name       = var.public_hostname
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-viewer"
    Component          = "edge"
    Role               = "viewer-certificate"
    DataClassification = "public"
  })
}

resource "aws_route53_record" "viewer_certificate_validation" {
  for_each = {
    for option in aws_acm_certificate.viewer.domain_validation_options :
    option.domain_name => {
      name   = option.resource_record_name
      record = option.resource_record_value
      type   = option.resource_record_type
    }
  }

  zone_id         = var.hosted_zone_id
  name            = each.value.name
  type            = each.value.type
  ttl             = 60
  records         = [each.value.record]
  allow_overwrite = true
}

resource "aws_acm_certificate_validation" "viewer" {
  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.viewer.arn
  validation_record_fqdns = [for record in aws_route53_record.viewer_certificate_validation : record.fqdn]
}

resource "aws_cloudfront_distribution" "main" {
  enabled         = true
  is_ipv6_enabled = true
  comment         = "Public edge for ${var.public_hostname}"
  aliases         = [var.public_hostname]
  http_version    = "http2and3"
  price_class     = var.cloudfront_price_class

  origin {
    domain_name = var.app_origin_domain_name
    origin_id   = "app-origin-default"

    custom_origin_config {
      http_port                = 80
      https_port               = 443
      origin_protocol_policy   = "http-only"
      origin_ssl_protocols     = ["TLSv1.2"]
      origin_read_timeout      = var.default_app_origin_read_timeout_seconds
      origin_keepalive_timeout = var.origin_keepalive_timeout_seconds
    }
  }

  origin {
    domain_name = var.app_origin_domain_name
    origin_id   = "app-origin-ag-ui"

    custom_origin_config {
      http_port                = 80
      https_port               = 443
      origin_protocol_policy   = "http-only"
      origin_ssl_protocols     = ["TLSv1.2"]
      origin_read_timeout      = var.ag_ui_origin_read_timeout_seconds
      origin_keepalive_timeout = var.origin_keepalive_timeout_seconds
    }
  }

  origin {
    domain_name              = var.product_image_bucket_regional_domain_name
    origin_id                = "product-images-s3"
    origin_access_control_id = aws_cloudfront_origin_access_control.product_images.id

    s3_origin_config {
      origin_access_identity = ""
    }
  }

  default_cache_behavior {
    target_origin_id         = "app-origin-default"
    viewer_protocol_policy   = "redirect-to-https"
    allowed_methods          = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods           = ["GET", "HEAD", "OPTIONS"]
    cache_policy_id          = aws_cloudfront_cache_policy.dynamic_disabled.id
    origin_request_policy_id = aws_cloudfront_origin_request_policy.dynamic_all_viewer.id
    compress                 = true
  }

  ordered_cache_behavior {
    path_pattern             = "/ag-ui/*"
    target_origin_id         = "app-origin-ag-ui"
    viewer_protocol_policy   = "redirect-to-https"
    allowed_methods          = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods           = ["GET", "HEAD", "OPTIONS"]
    cache_policy_id          = aws_cloudfront_cache_policy.dynamic_disabled.id
    origin_request_policy_id = aws_cloudfront_origin_request_policy.dynamic_all_viewer.id
    compress                 = false
  }

  ordered_cache_behavior {
    path_pattern           = "/static/product-images/*"
    target_origin_id       = "product-images-s3"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD", "OPTIONS"]
    cache_policy_id        = aws_cloudfront_cache_policy.product_images.id
    compress               = true
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.viewer.certificate_arn
    minimum_protocol_version = "TLSv1.2_2021"
    ssl_support_method       = "sni-only"
  }

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-cloudfront"
    Component          = "edge"
    Role               = "distribution"
    DataClassification = "public"
  })
}

resource "aws_route53_record" "public_a" {
  zone_id         = var.hosted_zone_id
  name            = var.public_hostname
  type            = "A"
  allow_overwrite = true

  alias {
    evaluate_target_health = false
    name                   = aws_cloudfront_distribution.main.domain_name
    zone_id                = aws_cloudfront_distribution.main.hosted_zone_id
  }
}

resource "aws_route53_record" "public_aaaa" {
  zone_id         = var.hosted_zone_id
  name            = var.public_hostname
  type            = "AAAA"
  allow_overwrite = true

  alias {
    evaluate_target_health = false
    name                   = aws_cloudfront_distribution.main.domain_name
    zone_id                = aws_cloudfront_distribution.main.hosted_zone_id
  }
}
