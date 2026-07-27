output "raw_bucket_name" {
  value       = aws_s3_bucket.raw.id
  description = "S3 bucket used for immutable raw telemetry."
}

output "warehouse_endpoint" {
  value       = aws_db_instance.warehouse.address
  description = "Private RDS hostname."
}

output "database_secret_arn" {
  value       = aws_db_instance.warehouse.master_user_secret[0].secret_arn
  description = "AWS-managed Secrets Manager ARN containing warehouse credentials."
}

output "pipeline_ecr_repository" {
  value       = aws_ecr_repository.pipeline.repository_url
  description = "Push the pipeline Docker image here before enabling scheduled runs."
}

output "pipeline_ecs_cluster" {
  value       = aws_ecs_cluster.pipeline.name
  description = "ECS cluster containing the scheduled Fargate task."
}

output "pipeline_log_group" {
  value       = aws_cloudwatch_log_group.pipeline.name
  description = "CloudWatch log group for ingestion and dbt output."
}

output "dashboard_ecr_repository" {
  value       = aws_ecr_repository.dashboard.repository_url
  description = "Push the Streamlit Docker image here before enabling its service."
}

output "dashboard_url" {
  value       = var.deploy_dashboard ? "http://${aws_lb.dashboard[0].dns_name}" : null
  description = "Dashboard URL when deploy_dashboard is enabled."
}
