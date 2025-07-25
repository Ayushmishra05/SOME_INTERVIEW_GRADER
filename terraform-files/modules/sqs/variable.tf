variable "queue_name" {
  description = "The name of the SQS queue"
  type        = string
}

variable "source_bucket_arn" {
  description = "ARN of the S3 bucket to allow sending messages"
  type        = string
}