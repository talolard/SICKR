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

resource "aws_security_group" "app_host" {
  name        = "${var.name_prefix}-app-host"
  description = "Internet-facing security group for the single EC2 origin host."
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "UI origin traffic for CloudFront default behavior"
    from_port   = var.app_ui_origin_port
    to_port     = var.app_ui_origin_port
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Backend AG-UI origin traffic for CloudFront streaming behavior"
    from_port   = var.app_backend_origin_port
    to_port     = var.app_backend_origin_port
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow the host to pull images, packages, and reach AWS APIs"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-app-host"
    Component          = "network"
    Role               = "app-host-sg"
    DataClassification = "internal"
  })
}

resource "aws_security_group" "database" {
  name        = "${var.name_prefix}-database"
  description = "Private PostgreSQL access from the single app host only."
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL from the app host security group"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app_host.id]
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
