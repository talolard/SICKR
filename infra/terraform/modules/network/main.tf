locals {
  public_subnets = {
    for index, cidr_block in var.public_subnet_cidrs :
    format("public-%02d", index + 1) => {
      availability_zone = var.availability_zones[index]
      cidr_block        = cidr_block
    }
  }

  database_subnets = {
    for index, cidr_block in var.database_subnet_cidrs :
    format("database-%02d", index + 1) => {
      availability_zone = var.availability_zones[index]
      cidr_block        = cidr_block
    }
  }
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-vpc"
    Component          = "network"
    Role               = "vpc"
    DataClassification = "internal"
  })
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-igw"
    Component          = "network"
    Role               = "internet-gateway"
    DataClassification = "internal"
  })
}

resource "aws_subnet" "public" {
  for_each = local.public_subnets

  vpc_id                  = aws_vpc.main.id
  cidr_block              = each.value.cidr_block
  availability_zone       = each.value.availability_zone
  map_public_ip_on_launch = true

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-${each.key}"
    Component          = "network"
    Role               = "public-subnet"
    DataClassification = "internal"
  })
}

resource "aws_subnet" "database" {
  for_each = local.database_subnets

  vpc_id            = aws_vpc.main.id
  cidr_block        = each.value.cidr_block
  availability_zone = each.value.availability_zone

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-${each.key}"
    Component          = "network"
    Role               = "database-subnet"
    DataClassification = "private"
  })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-public"
    Component          = "network"
    Role               = "public-route-table"
    DataClassification = "internal"
  })
}

resource "aws_route_table" "database" {
  for_each = aws_subnet.database

  vpc_id = aws_vpc.main.id

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-${each.key}"
    Component          = "network"
    Role               = "database-route-table"
    DataClassification = "private"
  })
}

resource "aws_route" "public_internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main.id
}

resource "aws_route_table_association" "public" {
  for_each = aws_subnet.public

  subnet_id      = each.value.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "database" {
  for_each = aws_subnet.database

  subnet_id      = each.value.id
  route_table_id = aws_route_table.database[each.key].id
}

resource "aws_security_group" "alb" {
  name        = "${var.name_prefix}-alb"
  description = "Public ingress security group for the application load balancer."
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "Public HTTP ingress for CloudFront and direct fallback access"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow the ALB to reach the ECS services"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-alb"
    Component          = "network"
    Role               = "alb-sg"
    DataClassification = "internal"
  })
}

resource "aws_vpc_security_group_ingress_rule" "alb_backend_proxy_from_ui" {
  security_group_id            = aws_security_group.alb.id
  referenced_security_group_id = aws_security_group.ui_service.id
  from_port                    = var.app_backend_origin_port
  to_port                      = var.app_backend_origin_port
  ip_protocol                  = "tcp"
  description                  = "Internal backend proxy ingress from the UI ECS service"
}

resource "aws_security_group" "ui_service" {
  name        = "${var.name_prefix}-ui-service"
  description = "UI ECS service ingress from the ALB only."
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "UI traffic from the ALB"
    from_port       = var.app_ui_origin_port
    to_port         = var.app_ui_origin_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    description = "Allow UI tasks to reach the internet and AWS APIs"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-ui-service"
    Component          = "network"
    Role               = "ui-service-sg"
    DataClassification = "internal"
  })
}

resource "aws_security_group" "backend_service" {
  name        = "${var.name_prefix}-backend-service"
  description = "Backend ECS service ingress from the ALB only."
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Backend traffic from the ALB"
    from_port       = var.app_backend_origin_port
    to_port         = var.app_backend_origin_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    description = "Allow backend tasks to reach the internet and AWS APIs"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-backend-service"
    Component          = "network"
    Role               = "backend-service-sg"
    DataClassification = "internal"
  })
}

resource "aws_security_group" "database" {
  name = "${var.name_prefix}-database"
  # Keep the legacy description stable so Terraform can update the ingress rule
  # in place during the EC2 -> ECS runtime migration instead of replacing the SG
  # that Aurora is already attached to.
  description = "Private PostgreSQL access from the single app host only."
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL from the backend ECS service security group"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.backend_service.id]
  }

  egress {
    description = "Allow Aurora-managed control plane traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-database"
    Component          = "network"
    Role               = "database-sg"
    DataClassification = "private"
  })
}
