data "aws_partition" "current" {}

data "aws_iam_policy_document" "ecs_task_assume_role" {
  statement {
    sid     = "EcsTasksAssumeRole"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "task_execution_access" {
  statement {
    sid    = "ReadRuntimeSecrets"
    effect = "Allow"
    actions = [
      "secretsmanager:DescribeSecret",
      "secretsmanager:GetSecretValue",
    ]
    resources = [
      var.backend_app_secret_arn,
      var.model_provider_secret_arn,
      var.observability_secret_arn,
      var.database_secret_arn,
    ]
  }
}

data "aws_iam_policy_document" "backend_task_access" {
  statement {
    sid    = "PrivateArtifactsBucket"
    effect = "Allow"
    actions = [
      "s3:ListBucket",
    ]
    resources = [
      "arn:${data.aws_partition.current.partition}:s3:::${var.private_artifacts_bucket_name}",
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
      "arn:${data.aws_partition.current.partition}:s3:::${var.private_artifacts_bucket_name}/*",
    ]
  }
}

data "aws_subnet" "public" {
  for_each = toset(var.public_subnet_ids)
  id       = each.value
}

locals {
  placeholder_image      = "public.ecr.aws/docker/library/busybox:stable"
  backend_artifact_root  = "/var/lib/ikea-agent/artifacts"
  backend_log_group_name = "/ecs/${var.name_prefix}/backend"
  ui_log_group_name      = "/ecs/${var.name_prefix}/ui"
  backend_container_name = "backend"
  ui_container_name      = "ui"
  vpc_id                 = one(distinct([for subnet in data.aws_subnet.public : subnet.vpc_id]))
  alb_dns_url            = "http://${aws_lb.main.dns_name}"
  backend_proxy_base_url = "http://${aws_lb.main.dns_name}:${var.backend_container_port}/"
  backend_environment = [
    { name = "APP_ENV", value = var.environment },
    { name = "LOG_LEVEL", value = "INFO" },
    { name = "LOG_JSON", value = "true" },
    { name = "LOGFIRE_SERVICE_NAME", value = "ikea-agent" },
    { name = "LOGFIRE_SERVICE_VERSION", value = "bootstrap" },
    { name = "LOGFIRE_ENVIRONMENT", value = var.environment },
    { name = "LOGFIRE_SEND_MODE", value = "if-token-present" },
    { name = "DATABASE_POOL_MODE", value = "nullpool" },
    { name = "ALLOW_MODEL_REQUESTS", value = "1" },
    { name = "IMAGE_SERVING_STRATEGY", value = "direct_public_url" },
    { name = "IMAGE_SERVICE_BASE_URL", value = var.product_image_base_url },
    { name = "ARTIFACT_ROOT_DIR", value = local.backend_artifact_root },
    { name = "ARTIFACT_STORAGE_BACKEND", value = "s3" },
    { name = "ARTIFACT_S3_BUCKET", value = var.private_artifacts_bucket_name },
    { name = "ARTIFACT_S3_PREFIX", value = var.environment },
    { name = "ARTIFACT_S3_REGION", value = var.region },
    { name = "FEEDBACK_CAPTURE_ENABLED", value = "0" },
    { name = "TRACE_CAPTURE_ENABLED", value = "0" },
  ]
  backend_secrets = [
    { name = "DATABASE_URL", valueFrom = "${var.database_secret_arn}:DATABASE_URL::" },
    { name = "GEMINI_API_KEY", valueFrom = "${var.model_provider_secret_arn}:GEMINI_API_KEY::" },
    { name = "FAL_KEY", valueFrom = "${var.model_provider_secret_arn}:FAL_KEY::" },
    { name = "LOGFIRE_TOKEN", valueFrom = "${var.observability_secret_arn}:LOGFIRE_TOKEN::" },
  ]
  ui_environment = [
    { name = "NODE_ENV", value = "production" },
    { name = "APP_ENV", value = var.environment },
    { name = "APP_RELEASE_VERSION", value = "bootstrap" },
    { name = "PY_AG_UI_URL", value = "${local.alb_dns_url}/ag-ui/" },
    { name = "BACKEND_PROXY_BASE_URL", value = local.backend_proxy_base_url },
    { name = "NEXT_PUBLIC_USE_MOCK_AGENT", value = "0" },
    { name = "NEXT_PUBLIC_TRACE_CAPTURE_ENABLED", value = "0" },
  ]
}

resource "aws_iam_role" "task_execution" {
  name               = "${var.name_prefix}-ecs-task-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-ecs-task-execution"
    Component          = "runtime"
    Role               = "ecs-task-execution"
    DataClassification = "internal"
  })
}

resource "aws_iam_role_policy_attachment" "task_execution_managed" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "task_execution_access" {
  name   = "${var.name_prefix}-ecs-task-execution-secrets"
  role   = aws_iam_role.task_execution.id
  policy = data.aws_iam_policy_document.task_execution_access.json
}

resource "aws_iam_role" "backend_task" {
  name               = "${var.name_prefix}-backend-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-backend-task"
    Component          = "runtime"
    Role               = "backend-task"
    DataClassification = "internal"
  })
}

resource "aws_iam_role_policy" "backend_task_access" {
  name   = "${var.name_prefix}-backend-task-access"
  role   = aws_iam_role.backend_task.id
  policy = data.aws_iam_policy_document.backend_task_access.json
}

resource "aws_iam_role" "ui_task" {
  name               = "${var.name_prefix}-ui-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-ui-task"
    Component          = "runtime"
    Role               = "ui-task"
    DataClassification = "internal"
  })
}

resource "aws_cloudwatch_log_group" "backend" {
  name              = local.backend_log_group_name
  retention_in_days = var.log_retention_days

  tags = merge(var.common_tags, {
    Name               = local.backend_log_group_name
    Component          = "runtime"
    Role               = "backend-logs"
    DataClassification = "internal"
  })
}

resource "aws_cloudwatch_log_group" "ui" {
  name              = local.ui_log_group_name
  retention_in_days = var.log_retention_days

  tags = merge(var.common_tags, {
    Name               = local.ui_log_group_name
    Component          = "runtime"
    Role               = "ui-logs"
    DataClassification = "internal"
  })
}

resource "aws_ecs_cluster" "main" {
  name = "${var.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-cluster"
    Component          = "runtime"
    Role               = "cluster"
    DataClassification = "internal"
  })
}

resource "aws_lb" "main" {
  name               = "${var.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.alb_security_group_id]
  subnets            = var.public_subnet_ids

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-alb"
    Component          = "runtime"
    Role               = "alb"
    DataClassification = "public"
  })
}

resource "aws_lb_target_group" "ui" {
  name        = "${var.name_prefix}-ui"
  port        = var.ui_container_port
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = local.vpc_id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200-299"
    path                = "/api/health/live"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-ui"
    Component          = "runtime"
    Role               = "ui-target-group"
    DataClassification = "internal"
  })
}

resource "aws_lb_target_group" "backend" {
  name        = "${var.name_prefix}-backend"
  port        = var.backend_container_port
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = local.vpc_id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200-299"
    path                = "/api/health/live"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-backend"
    Component          = "runtime"
    Role               = "backend-target-group"
    DataClassification = "internal"
  })
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ui.arn
  }
}

resource "aws_lb_listener" "backend_proxy" {
  load_balancer_arn = aws_lb.main.arn
  port              = var.backend_container_port
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }
}

resource "aws_lb_listener_rule" "ag_ui" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }

  condition {
    path_pattern {
      values = ["/ag-ui/*"]
    }
  }
}

resource "aws_lb_listener_rule" "api_agents" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 90

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }

  condition {
    path_pattern {
      values = ["/api/agents*"]
    }
  }
}

resource "aws_lb_listener_rule" "api_health" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 95

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }

  condition {
    path_pattern {
      values = ["/api/health*"]
    }
  }
}

resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.name_prefix}-backend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = tostring(var.backend_task_cpu)
  memory                   = tostring(var.backend_task_memory)
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.backend_task.arn

  runtime_platform {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }

  container_definitions = jsonencode([
    {
      name      = local.backend_container_name
      image     = local.placeholder_image
      essential = true
      command   = ["sh", "-c", "sleep infinity"]
      portMappings = [
        {
          containerPort = var.backend_container_port
          hostPort      = var.backend_container_port
          protocol      = "tcp"
          appProtocol   = "http"
        }
      ]
      environment = local.backend_environment
      secrets     = local.backend_secrets
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.backend.name
          awslogs-region        = var.region
          awslogs-stream-prefix = "backend"
        }
      }
    }
  ])

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-backend"
    Component          = "runtime"
    Role               = "backend-task-definition"
    DataClassification = "internal"
  })
}

resource "aws_ecs_task_definition" "ui" {
  family                   = "${var.name_prefix}-ui"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = tostring(var.ui_task_cpu)
  memory                   = tostring(var.ui_task_memory)
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.ui_task.arn

  runtime_platform {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }

  container_definitions = jsonencode([
    {
      name      = local.ui_container_name
      image     = local.placeholder_image
      essential = true
      command   = ["sh", "-c", "sleep infinity"]
      portMappings = [
        {
          containerPort = var.ui_container_port
          hostPort      = var.ui_container_port
          protocol      = "tcp"
          appProtocol   = "http"
        }
      ]
      environment = local.ui_environment
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ui.name
          awslogs-region        = var.region
          awslogs-stream-prefix = "ui"
        }
      }
    }
  ])

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-ui"
    Component          = "runtime"
    Role               = "ui-task-definition"
    DataClassification = "internal"
  })
}

resource "aws_ecs_service" "backend" {
  name            = "${var.name_prefix}-backend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = var.initial_desired_count
  launch_type     = "FARGATE"

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  deployment_controller {
    type = "ECS"
  }

  network_configuration {
    subnets          = var.public_subnet_ids
    security_groups  = [var.backend_service_security_group_id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = local.backend_container_name
    container_port   = var.backend_container_port
  }

  lifecycle {
    ignore_changes = [desired_count, task_definition]
  }

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-backend"
    Component          = "runtime"
    Role               = "backend-service"
    DataClassification = "internal"
  })
}

resource "aws_ecs_service" "ui" {
  name            = "${var.name_prefix}-ui"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.ui.arn
  desired_count   = var.initial_desired_count
  launch_type     = "FARGATE"

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  deployment_controller {
    type = "ECS"
  }

  network_configuration {
    subnets          = var.public_subnet_ids
    security_groups  = [var.ui_service_security_group_id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.ui.arn
    container_name   = local.ui_container_name
    container_port   = var.ui_container_port
  }

  lifecycle {
    ignore_changes = [desired_count, task_definition]
  }

  tags = merge(var.common_tags, {
    Name               = "${var.name_prefix}-ui"
    Component          = "runtime"
    Role               = "ui-service"
    DataClassification = "internal"
  })
}
