# Terraform Outputs for Growth Fund Builder

output "ecr_repository_url" {
  description = "ECR repository URL for Docker images"
  value       = aws_ecr_repository.growth_fund.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "s3_bucket_name" {
  description = "S3 bucket for fund documents"
  value       = aws_s3_bucket.fund_docs.id
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.fund_docs.arn
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.growth_fund.name
}

output "secrets_manager_arn" {
  description = "Secrets Manager ARN for API keys"
  value       = aws_secretsmanager_secret.api_keys.arn
}

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnets
}

output "security_group_id" {
  description = "Security group ID for ECS tasks"
  value       = aws_security_group.ecs_tasks.id
}

output "sp500_task_definition_arn" {
  description = "SP500 task definition ARN"
  value       = aws_ecs_task_definition.sp500.arn
}

output "tase125_task_definition_arn" {
  description = "TASE125 task definition ARN"
  value       = aws_ecs_task_definition.tase125.arn
}

output "quarterly_schedule_rules" {
  description = "EventBridge quarterly schedule rule names"
  value = {
    q1 = aws_cloudwatch_event_rule.quarterly_q1.name
    q2 = aws_cloudwatch_event_rule.quarterly_q2.name
    q3 = aws_cloudwatch_event_rule.quarterly_q3.name
    q4 = aws_cloudwatch_event_rule.quarterly_q4.name
  }
}
