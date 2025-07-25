output "queue_url" {
  description = "URL of the created SQS queue"
  value       = aws_sqs_queue.this.id
}

output "queue_arn" {
  description = "ARN of the created SQS queue"
  value       = aws_sqs_queue.this.arn
}