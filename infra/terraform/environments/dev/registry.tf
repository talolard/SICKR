resource "aws_ecr_repository" "service" {
  for_each = local.ecr_repository_names

  name                 = each.value
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name               = each.value
    Component          = "registry"
    Role               = each.key
    DataClassification = "internal"
  }
}

resource "aws_ecr_lifecycle_policy" "service" {
  for_each = aws_ecr_repository.service

  repository = each.value.name
  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images quickly"
        selection = {
          tagStatus   = "untagged"
          countType   = "imageCountMoreThan"
          countNumber = 1
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Keep the most recent tagged release images"
        selection = {
          tagStatus      = "tagged"
          tagPatternList = ["v*", "sha-*"]
          countType      = "imageCountMoreThan"
          countNumber    = 50
        }
        action = {
          type = "expire"
        }
      },
    ]
  })
}
