resource "aws_s3_bucket" "lambda_bucket" {
  bucket = var.bucket_name
  force_destroy = true
}

resource "aws_s3_bucket_ownership_controls" "ownership" {
  bucket = aws_s3_bucket.lambda_bucket.id

  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_object" "lambda_object" {
  bucket = aws_s3_bucket.lambda_bucket.id
  key    = var.s3_key
  source = var.archive_path
  etag   = filemd5(var.archive_path)
}
