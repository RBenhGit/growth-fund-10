# Terraform Variables for Growth Fund Builder AWS Deployment

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (prod, staging, dev)"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "growth-fund-builder"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24"]
}

variable "task_cpu" {
  description = "CPU units for ECS task (1024 = 1 vCPU)"
  type        = string
  default     = "2048"  # 2 vCPUs
}

variable "task_memory" {
  description = "Memory for ECS task in MB"
  type        = string
  default     = "4096"  # 4 GB
}

variable "twelvedata_api_key" {
  description = "TwelveData API key"
  type        = string
  sensitive   = true
}

variable "alphavantage_api_key" {
  description = "Alpha Vantage API key (optional)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "schedule_timezone" {
  description = "Timezone for scheduled executions"
  type        = string
  default     = "UTC"
}
