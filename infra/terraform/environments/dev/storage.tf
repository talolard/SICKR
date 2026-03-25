module "storage" {
  source = "../../modules/storage"

  product_image_bucket_name     = local.product_image_bucket_name
  private_artifacts_bucket_name = local.private_artifacts_bucket_name
  common_tags                   = local.default_tags
}

data "aws_iam_policy_document" "product_images_cloudfront_read" {
  statement {
    sid    = "AllowCloudFrontReadOnlyViaOac"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    actions = ["s3:GetObject"]
    resources = [
      "${module.storage.product_image_bucket_arn}/*",
    ]

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [module.edge.cloudfront_distribution_arn]
    }
  }
}

resource "aws_s3_bucket_policy" "product_images_cloudfront" {
  bucket = module.storage.product_image_bucket_id
  policy = data.aws_iam_policy_document.product_images_cloudfront_read.json
}
