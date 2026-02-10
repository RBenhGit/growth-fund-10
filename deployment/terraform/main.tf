# AWS ECS Fargate deployment for Growth Fund Builder
# Quarterly scheduled execution with EventBridge

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Backend configuration for state management
  backend "s3" {
    bucket         = "growth-fund-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "growth-fund-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "GrowthFundBuilder"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# VPC and Networking
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.project_name}-vpc"
  cidr = var.vpc_cidr

  azs             = data.aws_availability_zones.available.names
  private_subnets = var.private_subnet_cidrs
  public_subnets  = var.public_subnet_cidrs

  enable_nat_gateway = true
  single_nat_gateway = true
  enable_dns_hostnames = true
  enable_dns_support   = true
}

# ECR Repository for Docker images
resource "aws_ecr_repository" "growth_fund" {
  name                 = "${var.project_name}-repo"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "growth_fund" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 30
}

# ECS Task Execution Role
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "${var.project_name}-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS Task Role (for application permissions)
resource "aws_iam_role" "ecs_task_role" {
  name = "${var.project_name}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

# Policy for ECS task to access S3 (for fund documents)
resource "aws_iam_policy" "ecs_task_policy" {
  name = "${var.project_name}-ecs-task-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.fund_docs.arn,
          "${aws_s3_bucket.fund_docs.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.api_keys.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_policy_attachment" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.ecs_task_policy.arn
}

# S3 Bucket for Fund Documents
resource "aws_s3_bucket" "fund_docs" {
  bucket = "${var.project_name}-fund-docs-${var.environment}"
}

resource "aws_s3_bucket_versioning" "fund_docs" {
  bucket = aws_s3_bucket.fund_docs.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_encryption" "fund_docs" {
  bucket = aws_s3_bucket.fund_docs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Secrets Manager for API Keys
resource "aws_secretsmanager_secret" "api_keys" {
  name = "${var.project_name}-api-keys-${var.environment}"
  description = "API keys for Growth Fund Builder"
}

resource "aws_secretsmanager_secret_version" "api_keys" {
  secret_id = aws_secretsmanager_secret.api_keys.id
  secret_string = jsonencode({
    TWELVEDATA_API_KEY = var.twelvedata_api_key
    ALPHAVANTAGE_API_KEY = var.alphavantage_api_key
  })
}

# ECS Task Definition for SP500
resource "aws_ecs_task_definition" "sp500" {
  family                   = "${var.project_name}-sp500"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([{
    name  = "growth-fund-sp500"
    image = "${aws_ecr_repository.growth_fund.repository_url}:latest"

    command = ["--index", "SP500"]

    environment = [
      { name = "US_FINANCIAL_DATA_SOURCE", value = "twelvedata" },
      { name = "US_PRICING_DATA_SOURCE", value = "yfinance" },
      { name = "USE_CACHE", value = "true" },
      { name = "DEBUG_MODE", value = "false" },
      { name = "OUTPUT_DIRECTORY", value = "/tmp/Fund_Docs" }
    ]

    secrets = [
      {
        name      = "TWELVEDATA_API_KEY"
        valueFrom = "${aws_secretsmanager_secret.api_keys.arn}:TWELVEDATA_API_KEY::"
      },
      {
        name      = "ALPHAVANTAGE_API_KEY"
        valueFrom = "${aws_secretsmanager_secret.api_keys.arn}:ALPHAVANTAGE_API_KEY::"
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.growth_fund.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "sp500"
      }
    }
  }])
}

# ECS Task Definition for TASE125
resource "aws_ecs_task_definition" "tase125" {
  family                   = "${var.project_name}-tase125"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([{
    name  = "growth-fund-tase125"
    image = "${aws_ecr_repository.growth_fund.repository_url}:latest"

    command = ["--index", "TASE125"]

    environment = [
      { name = "TASE_FINANCIAL_DATA_SOURCE", value = "twelvedata" },
      { name = "TASE_PRICING_DATA_SOURCE", value = "yfinance" },
      { name = "USE_CACHE", value = "true" },
      { name = "DEBUG_MODE", value = "false" },
      { name = "OUTPUT_DIRECTORY", value = "/tmp/Fund_Docs" }
    ]

    secrets = [
      {
        name      = "TWELVEDATA_API_KEY"
        valueFrom = "${aws_secretsmanager_secret.api_keys.arn}:TWELVEDATA_API_KEY::"
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.growth_fund.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "tase125"
      }
    }
  }])
}

# Security Group for ECS Tasks
resource "aws_security_group" "ecs_tasks" {
  name        = "${var.project_name}-ecs-tasks-sg"
  description = "Security group for Growth Fund Builder ECS tasks"
  vpc_id      = module.vpc.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# EventBridge Role
resource "aws_iam_role" "eventbridge_role" {
  name = "${var.project_name}-eventbridge-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "events.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "eventbridge_ecs_policy" {
  name = "${var.project_name}-eventbridge-ecs-policy"
  role = aws_iam_role.eventbridge_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "ecs:RunTask"
      ]
      Resource = [
        aws_ecs_task_definition.sp500.arn,
        aws_ecs_task_definition.tase125.arn
      ]
    }, {
      Effect = "Allow"
      Action = [
        "iam:PassRole"
      ]
      Resource = [
        aws_iam_role.ecs_task_execution_role.arn,
        aws_iam_role.ecs_task_role.arn
      ]
    }]
  })
}

# EventBridge Rule for Quarterly Execution - Q1 (January 1st)
resource "aws_cloudwatch_event_rule" "quarterly_q1" {
  name                = "${var.project_name}-quarterly-q1"
  description         = "Trigger fund build on Q1 (January 1st)"
  schedule_expression = "cron(0 6 1 1 ? *)"  # 6 AM UTC on January 1st
}

# EventBridge Rule for Quarterly Execution - Q2 (April 1st)
resource "aws_cloudwatch_event_rule" "quarterly_q2" {
  name                = "${var.project_name}-quarterly-q2"
  description         = "Trigger fund build on Q2 (April 1st)"
  schedule_expression = "cron(0 6 1 4 ? *)"  # 6 AM UTC on April 1st
}

# EventBridge Rule for Quarterly Execution - Q3 (July 1st)
resource "aws_cloudwatch_event_rule" "quarterly_q3" {
  name                = "${var.project_name}-quarterly-q3"
  description         = "Trigger fund build on Q3 (July 1st)"
  schedule_expression = "cron(0 6 1 7 ? *)"  # 6 AM UTC on July 1st
}

# EventBridge Rule for Quarterly Execution - Q4 (October 1st)
resource "aws_cloudwatch_event_rule" "quarterly_q4" {
  name                = "${var.project_name}-quarterly-q4"
  description         = "Trigger fund build on Q4 (October 1st)"
  schedule_expression = "cron(0 6 1 10 ? *)"  # 6 AM UTC on October 1st
}

# EventBridge Targets - SP500
resource "aws_cloudwatch_event_target" "sp500_q1" {
  rule      = aws_cloudwatch_event_rule.quarterly_q1.name
  arn       = aws_ecs_cluster.main.arn
  role_arn  = aws_iam_role.eventbridge_role.arn

  ecs_target {
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.sp500.arn
    launch_type         = "FARGATE"
    platform_version    = "LATEST"

    network_configuration {
      subnets          = module.vpc.private_subnets
      security_groups  = [aws_security_group.ecs_tasks.id]
      assign_public_ip = false
    }
  }
}

resource "aws_cloudwatch_event_target" "sp500_q2" {
  rule      = aws_cloudwatch_event_rule.quarterly_q2.name
  arn       = aws_ecs_cluster.main.arn
  role_arn  = aws_iam_role.eventbridge_role.arn

  ecs_target {
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.sp500.arn
    launch_type         = "FARGATE"
    platform_version    = "LATEST"

    network_configuration {
      subnets          = module.vpc.private_subnets
      security_groups  = [aws_security_group.ecs_tasks.id]
      assign_public_ip = false
    }
  }
}

resource "aws_cloudwatch_event_target" "sp500_q3" {
  rule      = aws_cloudwatch_event_rule.quarterly_q3.name
  arn       = aws_ecs_cluster.main.arn
  role_arn  = aws_iam_role.eventbridge_role.arn

  ecs_target {
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.sp500.arn
    launch_type         = "FARGATE"
    platform_version    = "LATEST"

    network_configuration {
      subnets          = module.vpc.private_subnets
      security_groups  = [aws_security_group.ecs_tasks.id]
      assign_public_ip = false
    }
  }
}

resource "aws_cloudwatch_event_target" "sp500_q4" {
  rule      = aws_cloudwatch_event_rule.quarterly_q4.name
  arn       = aws_ecs_cluster.main.arn
  role_arn  = aws_iam_role.eventbridge_role.arn

  ecs_target {
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.sp500.arn
    launch_type         = "FARGATE"
    platform_version    = "LATEST"

    network_configuration {
      subnets          = module.vpc.private_subnets
      security_groups  = [aws_security_group.ecs_tasks.id]
      assign_public_ip = false
    }
  }
}

# EventBridge Targets - TASE125 (30 minutes after SP500)
resource "aws_cloudwatch_event_target" "tase125_q1" {
  rule      = aws_cloudwatch_event_rule.quarterly_q1.name
  arn       = aws_ecs_cluster.main.arn
  role_arn  = aws_iam_role.eventbridge_role.arn

  ecs_target {
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.tase125.arn
    launch_type         = "FARGATE"
    platform_version    = "LATEST"

    network_configuration {
      subnets          = module.vpc.private_subnets
      security_groups  = [aws_security_group.ecs_tasks.id]
      assign_public_ip = false
    }
  }
}

resource "aws_cloudwatch_event_target" "tase125_q2" {
  rule      = aws_cloudwatch_event_rule.quarterly_q2.name
  arn       = aws_ecs_cluster.main.arn
  role_arn  = aws_iam_role.eventbridge_role.arn

  ecs_target {
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.tase125.arn
    launch_type         = "FARGATE"
    platform_version    = "LATEST"

    network_configuration {
      subnets          = module.vpc.private_subnets
      security_groups  = [aws_security_group.ecs_tasks.id]
      assign_public_ip = false
    }
  }
}

resource "aws_cloudwatch_event_target" "tase125_q3" {
  rule      = aws_cloudwatch_event_rule.quarterly_q3.name
  arn       = aws_ecs_cluster.main.arn
  role_arn  = aws_iam_role.eventbridge_role.arn

  ecs_target {
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.tase125.arn
    launch_type         = "FARGATE"
    platform_version    = "LATEST"

    network_configuration {
      subnets          = module.vpc.private_subnets
      security_groups  = [aws_security_group.ecs_tasks.id]
      assign_public_ip = false
    }
  }
}

resource "aws_cloudwatch_event_target" "tase125_q4" {
  rule      = aws_cloudwatch_event_rule.quarterly_q4.name
  arn       = aws_ecs_cluster.main.arn
  role_arn  = aws_iam_role.eventbridge_role.arn

  ecs_target {
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.tase125.arn
    launch_type         = "FARGATE"
    platform_version    = "LATEST"

    network_configuration {
      subnets          = module.vpc.private_subnets
      security_groups  = [aws_security_group.ecs_tasks.id]
      assign_public_ip = false
    }
  }
}

# Data source for availability zones
data "aws_availability_zones" "available" {
  state = "available"
}
