module "sqs_queue" {
  source           = "./modules/sqs"
  queue_name       = var.queue_name[var.environment]
  source_bucket_arn = var.source_bucket_arn
}

resource "aws_s3_bucket_notification" "s3_to_sqs" {
  bucket = var.source_bucket_id

  queue {
    queue_arn = module.sqs_queue.queue_arn
    events    = ["s3:ObjectCreated:*"]
    filter_prefix = var.filter_prefix != "" ? var.filter_prefix : null
  }

  depends_on = [module.sqs_queue]
}
