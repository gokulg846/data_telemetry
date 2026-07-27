data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  name = "data-telemetry-${var.environment}"
}

resource "aws_vpc" "main" {
  cidr_block           = "10.40.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
}

resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  cidr_block              = "10.40.${count.index}.0/24"
  map_public_ip_on_launch = true
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  availability_zone = data.aws_availability_zones.available.names[count.index]
  cidr_block        = "10.40.${count.index + 10}.0/24"
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_s3_bucket" "raw" {
  bucket = "${local.name}-raw-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_versioning" "raw" {
  bucket = aws_s3_bucket.raw.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "raw" {
  bucket = aws_s3_bucket.raw.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "raw" {
  bucket                  = aws_s3_bucket.raw.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "raw" {
  bucket = aws_s3_bucket.raw.id
  rule {
    id     = "archive-old-raw-data"
    status = "Enabled"
    filter {}
    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }
  }
}

resource "aws_db_subnet_group" "warehouse" {
  name       = "${local.name}-warehouse"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_security_group" "warehouse" {
  name        = "${local.name}-warehouse"
  description = "PostgreSQL access for telemetry application"
  vpc_id      = aws_vpc.main.id

  ingress {
    description              = "PostgreSQL from the pipeline task"
    from_port                = 5432
    to_port                  = 5432
    protocol                 = "tcp"
    source_security_group_id = aws_security_group.pipeline.id
  }

  ingress {
    description              = "PostgreSQL from the dashboard task"
    from_port                = 5432
    to_port                  = 5432
    protocol                 = "tcp"
    source_security_group_id = aws_security_group.dashboard.id
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "warehouse" {
  identifier                   = "${local.name}-warehouse"
  engine                       = "postgres"
  engine_version               = "16"
  instance_class               = var.database_instance_class
  allocated_storage            = 20
  max_allocated_storage        = 100
  storage_encrypted            = true
  db_name                      = "telemetry"
  username                     = "telemetry_admin"
  manage_master_user_password  = true
  db_subnet_group_name         = aws_db_subnet_group.warehouse.name
  vpc_security_group_ids       = [aws_security_group.warehouse.id]
  publicly_accessible          = false
  backup_retention_period      = 7
  auto_minor_version_upgrade   = true
  deletion_protection          = var.environment == "prod"
  skip_final_snapshot          = var.environment != "prod"
  performance_insights_enabled = true
}

resource "aws_ecr_repository" "pipeline" {
  name                 = "${local.name}-pipeline"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "pipeline" {
  repository = aws_ecr_repository.pipeline.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the ten newest pipeline images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}

resource "aws_ecr_repository" "dashboard" {
  name                 = "${local.name}-dashboard"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecs_cluster" "pipeline" {
  name = "${local.name}-pipeline"
}

resource "aws_cloudwatch_log_group" "pipeline" {
  name              = "/ecs/${local.name}-pipeline"
  retention_in_days = 30
}

resource "aws_security_group" "pipeline" {
  name        = "${local.name}-pipeline"
  description = "Outbound access for scheduled telemetry tasks"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "dashboard_alb" {
  name        = "${local.name}-dashboard-alb"
  description = "Public HTTP access to the dashboard load balancer"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "dashboard" {
  name        = "${local.name}-dashboard"
  description = "Streamlit access from its load balancer"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port                = 8501
    to_port                  = 8501
    protocol                 = "tcp"
    source_security_group_id = aws_security_group.dashboard_alb.id
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_execution" {
  name               = "${local.name}-ecs-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_execution_secret" {
  name = "read-database-secret"
  role = aws_iam_role.ecs_execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = aws_db_instance.warehouse.master_user_secret[0].secret_arn
    }]
  })
}

resource "aws_iam_role" "pipeline_task" {
  name               = "${local.name}-pipeline-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy" "pipeline_s3" {
  name = "raw-bucket-access"
  role = aws_iam_role.pipeline_task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = aws_s3_bucket.raw.arn
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject"]
        Resource = "${aws_s3_bucket.raw.arn}/*"
      }
    ]
  })
}

resource "aws_ecs_task_definition" "pipeline" {
  family                   = "${local.name}-pipeline"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.pipeline_task.arn

  container_definitions = jsonencode([{
    name      = "pipeline"
    image     = "${aws_ecr_repository.pipeline.repository_url}:${var.pipeline_image_tag}"
    essential = true
    environment = [
      { name = "POSTGRES_HOST", value = aws_db_instance.warehouse.address },
      { name = "POSTGRES_PORT", value = tostring(aws_db_instance.warehouse.port) },
      { name = "POSTGRES_DB", value = aws_db_instance.warehouse.db_name },
      { name = "POSTGRES_USER", value = aws_db_instance.warehouse.username },
      { name = "S3_ENDPOINT_URL", value = "" },
      { name = "S3_BUCKET", value = aws_s3_bucket.raw.id },
      { name = "S3_REGION", value = var.aws_region }
    ]
    secrets = [{
      name      = "POSTGRES_PASSWORD"
      valueFrom = "${aws_db_instance.warehouse.master_user_secret[0].secret_arn}:password::"
    }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.pipeline.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "flow"
      }
    }
  }])
}

resource "aws_cloudwatch_log_group" "dashboard" {
  name              = "/ecs/${local.name}-dashboard"
  retention_in_days = 30
}

resource "aws_ecs_task_definition" "dashboard" {
  family                   = "${local.name}-dashboard"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_execution.arn

  container_definitions = jsonencode([{
    name      = "dashboard"
    image     = "${aws_ecr_repository.dashboard.repository_url}:${var.dashboard_image_tag}"
    essential = true
    portMappings = [{
      containerPort = 8501
      hostPort      = 8501
      protocol      = "tcp"
    }]
    environment = [
      { name = "POSTGRES_HOST", value = aws_db_instance.warehouse.address },
      { name = "POSTGRES_PORT", value = tostring(aws_db_instance.warehouse.port) },
      { name = "POSTGRES_DB", value = aws_db_instance.warehouse.db_name },
      { name = "POSTGRES_USER", value = aws_db_instance.warehouse.username }
    ]
    secrets = [{
      name      = "POSTGRES_PASSWORD"
      valueFrom = "${aws_db_instance.warehouse.master_user_secret[0].secret_arn}:password::"
    }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.dashboard.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "web"
      }
    }
  }])
}

resource "aws_lb" "dashboard" {
  count              = var.deploy_dashboard ? 1 : 0
  name               = "${local.name}-dashboard"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.dashboard_alb.id]
  subnets            = aws_subnet.public[*].id
}

resource "aws_lb_target_group" "dashboard" {
  count       = var.deploy_dashboard ? 1 : 0
  name        = "${local.name}-dashboard"
  port        = 8501
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = aws_vpc.main.id

  health_check {
    path                = "/_stcore/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

resource "aws_lb_listener" "dashboard" {
  count             = var.deploy_dashboard ? 1 : 0
  load_balancer_arn = aws_lb.dashboard[0].arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.dashboard[0].arn
  }
}

resource "aws_ecs_service" "dashboard" {
  count           = var.deploy_dashboard ? 1 : 0
  name            = "${local.name}-dashboard"
  cluster         = aws_ecs_cluster.pipeline.id
  task_definition = aws_ecs_task_definition.dashboard.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.dashboard.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.dashboard[0].arn
    container_name   = "dashboard"
    container_port   = 8501
  }

  depends_on = [aws_lb_listener.dashboard]
}

data "aws_iam_policy_document" "scheduler_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "${local.name}-scheduler"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume.json
}

resource "aws_iam_role_policy" "scheduler" {
  name = "run-pipeline-task"
  role = aws_iam_role.scheduler.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ecs:RunTask"]
        Resource = aws_ecs_task_definition.pipeline.arn
        Condition = {
          ArnLike = { "ecs:cluster" = aws_ecs_cluster.pipeline.arn }
        }
      },
      {
        Effect = "Allow"
        Action = ["iam:PassRole"]
        Resource = [
          aws_iam_role.ecs_execution.arn,
          aws_iam_role.pipeline_task.arn
        ]
      }
    ]
  })
}

resource "aws_scheduler_schedule" "pipeline" {
  name                = "${local.name}-hourly"
  schedule_expression = var.pipeline_schedule
  state               = var.enable_pipeline_schedule ? "ENABLED" : "DISABLED"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_ecs_cluster.pipeline.arn
    role_arn = aws_iam_role.scheduler.arn

    ecs_parameters {
      task_definition_arn = aws_ecs_task_definition.pipeline.arn
      launch_type         = "FARGATE"
      network_configuration {
        subnets          = aws_subnet.public[*].id
        security_groups  = [aws_security_group.pipeline.id]
        assign_public_ip = true
      }
    }
  }
}
