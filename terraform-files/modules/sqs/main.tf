resource "aws_sqs_queue" "this" {
  name = var.queue_name

  # Add any queue-specific settings here if needed (e.g., delay_seconds, kms_master_key_id)
}

resource "aws_sqs_queue_policy" "allow_s3" {
  queue_url = aws_sqs_queue.this.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect    = "Allow",
      Principal = { Service = "s3.amazonaws.com" },
      Action    = "SQS:SendMessage",
      Resource  = aws_sqs_queue.this.arn,
      Condition = {
        ArnEquals = {
          "aws:SourceArn" = var.source_bucket_arn
        }
      }
    }]
  })
}
