data "aws_partition" "current" {}

data "aws_iam_policy_document" "github_oidc_assume_role" {
  statement {
    sid     = "GitHubOidcAssumeRole"
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.github_oidc_provider_host}:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "ForAnyValue:StringLike"
      variable = "${local.github_oidc_provider_host}:sub"
      values   = local.github_release_subjects
    }
  }
}

data "aws_iam_policy_document" "runtime_assume_role" {
  statement {
    sid     = "Ec2AssumeRole"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "terraform_apply_assume_role" {
  statement {
    sid     = "AccountRootAssumeRole"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "AWS"
      identifiers = ["arn:${data.aws_partition.current.partition}:iam::${var.aws_account_id}:root"]
    }
  }
}

data "aws_iam_policy_document" "runtime_access" {
  statement {
    sid       = "EcrAuthorization"
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid    = "EcrPull"
    effect = "Allow"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:DescribeImages",
      "ecr:DescribeRepositories",
      "ecr:GetDownloadUrlForLayer",
    ]
    resources = [for repository in aws_ecr_repository.service : repository.arn]
  }

  statement {
    sid    = "ReadRuntimeSecrets"
    effect = "Allow"
    actions = [
      "secretsmanager:DescribeSecret",
      "secretsmanager:GetSecretValue",
    ]
    resources = local.runtime_secret_arns
  }

  statement {
    sid    = "PrivateArtifactsBucket"
    effect = "Allow"
    actions = [
      "s3:ListBucket",
    ]
    resources = [
      "arn:${data.aws_partition.current.partition}:s3:::${local.private_artifacts_bucket_name}",
    ]
  }

  statement {
    sid    = "PrivateArtifactsObjects"
    effect = "Allow"
    actions = [
      "s3:AbortMultipartUpload",
      "s3:DeleteObject",
      "s3:GetObject",
      "s3:PutObject",
    ]
    resources = [
      "arn:${data.aws_partition.current.partition}:s3:::${local.private_artifacts_bucket_name}/*",
    ]
  }

  statement {
    sid    = "ProductImagesReadOnly"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:ListBucket",
    ]
    resources = [
      "arn:${data.aws_partition.current.partition}:s3:::${local.product_image_bucket_name}",
      "arn:${data.aws_partition.current.partition}:s3:::${local.product_image_bucket_name}/*",
    ]
  }
}

data "aws_iam_policy_document" "release_publish_access" {
  statement {
    sid       = "EcrAuthorization"
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid    = "ReleaseImagePush"
    effect = "Allow"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:CompleteLayerUpload",
      "ecr:DescribeImages",
      "ecr:DescribeRepositories",
      "ecr:GetDownloadUrlForLayer",
      "ecr:InitiateLayerUpload",
      "ecr:ListImages",
      "ecr:PutImage",
      "ecr:UploadLayerPart",
    ]
    resources = [for repository in aws_ecr_repository.service : repository.arn]
  }
}

data "aws_iam_policy_document" "deploy_access" {
  statement {
    sid    = "InstanceDiscovery"
    effect = "Allow"
    actions = [
      "ec2:DescribeInstances",
      "ssm:DescribeInstanceInformation",
      "ssm:GetCommandInvocation",
      "ssm:ListCommandInvocations",
      "ssm:ListCommands",
      "ssm:SendCommand",
    ]
    resources = ["*"]
  }
}

data "aws_iam_policy_document" "terraform_apply_access" {
  statement {
    sid    = "TerraformApplyAwsSurface"
    effect = "Allow"
    actions = [
      "acm:*",
      "cloudfront:*",
      "ec2:*",
      "ecr:*",
      "iam:*",
      "rds:*",
      "route53:*",
      "s3:*",
      "secretsmanager:*",
      "ssm:*",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_openid_connect_provider" "github" {
  url            = local.github_oidc_provider_url
  client_id_list = ["sts.amazonaws.com"]

  tags = {
    Name               = "${local.name_prefix}-github-oidc"
    Component          = "identity"
    Role               = "github-oidc"
    DataClassification = "internal"
  }
}

resource "aws_iam_role" "runtime" {
  name               = local.runtime_role_name
  assume_role_policy = data.aws_iam_policy_document.runtime_assume_role.json

  tags = {
    Name               = local.runtime_role_name
    Component          = "identity"
    Role               = "runtime"
    DataClassification = "internal"
  }
}

resource "aws_iam_instance_profile" "runtime" {
  name = local.runtime_instance_profile
  role = aws_iam_role.runtime.name

  tags = {
    Name               = local.runtime_instance_profile
    Component          = "identity"
    Role               = "runtime"
    DataClassification = "internal"
  }
}

resource "aws_iam_role_policy_attachment" "runtime_ssm_core" {
  role       = aws_iam_role.runtime.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "runtime_access" {
  name   = "${local.runtime_role_name}-access"
  role   = aws_iam_role.runtime.id
  policy = data.aws_iam_policy_document.runtime_access.json
}

resource "aws_iam_role" "release_publish" {
  name               = local.release_publish_role_name
  assume_role_policy = data.aws_iam_policy_document.github_oidc_assume_role.json

  tags = {
    Name               = local.release_publish_role_name
    Component          = "identity"
    Role               = "release-publish"
    DataClassification = "internal"
  }
}

resource "aws_iam_role_policy" "release_publish_access" {
  name   = "${local.release_publish_role_name}-access"
  role   = aws_iam_role.release_publish.id
  policy = data.aws_iam_policy_document.release_publish_access.json
}

resource "aws_iam_role" "deploy" {
  name               = local.deploy_role_name
  assume_role_policy = data.aws_iam_policy_document.github_oidc_assume_role.json

  tags = {
    Name               = local.deploy_role_name
    Component          = "identity"
    Role               = "deploy"
    DataClassification = "internal"
  }
}

resource "aws_iam_role_policy" "deploy_access" {
  name   = "${local.deploy_role_name}-access"
  role   = aws_iam_role.deploy.id
  policy = data.aws_iam_policy_document.deploy_access.json
}

resource "aws_iam_role" "terraform_apply" {
  name               = local.terraform_apply_role_name
  assume_role_policy = data.aws_iam_policy_document.terraform_apply_assume_role.json

  tags = {
    Name               = local.terraform_apply_role_name
    Component          = "identity"
    Role               = "terraform-apply"
    DataClassification = "internal"
  }
}

resource "aws_iam_role_policy" "terraform_apply_access" {
  name   = "${local.terraform_apply_role_name}-access"
  role   = aws_iam_role.terraform_apply.id
  policy = data.aws_iam_policy_document.terraform_apply_access.json
}
