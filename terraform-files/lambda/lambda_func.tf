data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda-code"
  output_path = "${path.module}/lambda-code/video-upload.zip"
}

module "s3_bucket" {
  source         = "../modules/s3"
  bucket_name    = lookup(var.lambda_bucket_name, terraform.workspace)
  s3_key         = var.lambda_s3_key
  archive_path   = data.archive_file.lambda_zip.output_path
}

module "lambda_function" {
  source            = "../modules/lambda"
  function_name     = lookup(var.lambda_function_name, terraform.workspace)
  handler           = var.lambda_handler
  runtime           = var.lambda_runtime
  role_name         = lookup(var.lambda_role_name, terraform.workspace)
  log_retention     = var.lambda_log_retention

  bucket            = module.s3_bucket.bucket_id
  object_key        = module.s3_bucket.object_key
  source_code_hash  = data.archive_file.lambda_zip.output_base64sha256
}

module "rest_api" {
  source             = "../modules/api-gw"
  api_name           = lookup(var.api_gateway_name, terraform.workspace)
  resource_path      = var.api_resource_path
  stage_name         = var.api_stage_name
  region             = var.aws_region

  lambda_invoke_arn  = module.lambda_function.lambda_arn
  lambda_name        = module.lambda_function.lambda_name
}