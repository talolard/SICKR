resource "aws_s3_bucket" "product_images" {
  bucket = var.product_image_bucket_name

  tags = merge(var.common_tags, {
    Name               = var.product_image_bucket_name
    Component          = "storage"
    Role               = "product-images"
    DataClassification = "public"
  })
}

resource "aws_s3_bucket_public_access_block" "product_images" {
  bucket = aws_s3_bucket.product_images.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "product_images" {
  bucket = aws_s3_bucket.product_images.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "product_images" {
  bucket = aws_s3_bucket.product_images.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_ownership_controls" "product_images" {
  bucket = aws_s3_bucket.product_images.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket" "private_artifacts" {
  bucket = var.private_artifacts_bucket_name

  tags = merge(var.common_tags, {
    Name               = var.private_artifacts_bucket_name
    Component          = "storage"
    Role               = "private-artifacts"
    DataClassification = "private"
  })
}

resource "aws_s3_bucket_public_access_block" "private_artifacts" {
  bucket = aws_s3_bucket.private_artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "private_artifacts" {
  bucket = aws_s3_bucket.private_artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "private_artifacts" {
  bucket = aws_s3_bucket.private_artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_ownership_controls" "private_artifacts" {
  bucket = aws_s3_bucket.private_artifacts.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "private_artifacts" {
  bucket = aws_s3_bucket.private_artifacts.id

  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}
