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
      values   = local.github_actions_subjects
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
    sid    = "EcsDeployOperations"
    effect = "Allow"
    actions = [
      "elasticloadbalancing:DescribeLoadBalancers",
      "elasticloadbalancing:DescribeTargetGroups",
      "ecs:DescribeServices",
      "ecs:DescribeTaskDefinition",
      "ecs:DescribeTasks",
      "ecs:ListTasks",
      "ecs:RegisterTaskDefinition",
      "ecs:RunTask",
      "ecs:UpdateService",
    ]
    resources = ["*"]
  }

  statement {
    sid     = "PassEcsTaskRoles"
    effect  = "Allow"
    actions = ["iam:PassRole"]
    resources = [
      "arn:${data.aws_partition.current.partition}:iam::${var.aws_account_id}:role/${local.name_prefix}-ecs-task-execution",
      "arn:${data.aws_partition.current.partition}:iam::${var.aws_account_id}:role/${local.name_prefix}-backend-task",
      "arn:${data.aws_partition.current.partition}:iam::${var.aws_account_id}:role/${local.name_prefix}-ui-task",
    ]
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
      "ecs:*",
      "ecr:*",
      "elasticloadbalancing:*",
      "iam:*",
      "logs:*",
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
