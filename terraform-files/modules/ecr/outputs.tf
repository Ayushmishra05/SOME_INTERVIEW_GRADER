output "ecr_image_uri" {
  description = "Full ECR image URI with default 'latest' tag"
  value       = "${aws_ecr_repository.this.repository_url}:latest"
}

output "repository_arn" {
  description = "The ARN of the ECR repository"
  value       = aws_ecr_repository.this.arn
}