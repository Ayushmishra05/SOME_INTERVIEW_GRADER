output "bucket_id" {
  description = "ID of the S3 bucket used to store Lambda code"
  value       = aws_s3_bucket.lambda_bucket.id
}

output "object_key" {
  description = "S3 object key (file name) of the Lambda package"
  value       = aws_s3_object.lambda_object.key
}
