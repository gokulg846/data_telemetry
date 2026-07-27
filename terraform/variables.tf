variable "aws_region" {
  description = "AWS region for all resources."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment suffix used in resource names."
  type        = string
  default     = "dev"
}

variable "database_instance_class" {
  description = "RDS instance size. db.t4g.micro is suitable for a learning environment."
  type        = string
  default     = "db.t4g.micro"
}

variable "pipeline_schedule" {
  description = "EventBridge Scheduler expression for the ingestion and dbt task."
  type        = string
  default     = "rate(1 hour)"
}

variable "enable_pipeline_schedule" {
  description = "Enable the scheduled task only after the pipeline image is available in ECR."
  type        = bool
  default     = false
}

variable "pipeline_image_tag" {
  description = "Pipeline image tag already pushed to the managed ECR repository."
  type        = string
  default     = "latest"
}

variable "deploy_dashboard" {
  description = "Create the continuously running dashboard service and load balancer."
  type        = bool
  default     = false
}

variable "dashboard_image_tag" {
  description = "Dashboard image tag already pushed to its managed ECR repository."
  type        = string
  default     = "latest"
}
