variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "test", "prod"], var.environment)
    error_message = "Environment must be one of: dev, test, prod"
  }
}

variable "lambda_bucket_name" {
  type = map(string)
  default = {
    dev  = "some-lambda-artifacts-dev"
    test = "some-lambda-artifacts-test"
    prod = "some-lambda-artifacts-prod"
  }
}

variable "lambda_function_name" {
  type = map(string)
  default = {
    dev  = "video-upload-dev"
    test = "video-upload-stage"
    prod = "video-upload-prod"
  }
}

variable "lambda_handler" {
  type    = string
  default = "app.lambda_handler"
}

variable "lambda_runtime" {
  type    = string
  default = "python3.12"
}

variable "lambda_role_name" {
  type = map(string)
  default = {
    dev  = "lambda_exec_role_dev"
    test = "lambda_exec_role_test"
    prod = "lambda_exec_role_prod"
  }
}

variable "lambda_log_retention" {
  type    = number
  default = 14
}

variable "lambda_s3_key" {
  type    = string
  default = "video-upload.zip"
}

variable "api_gateway_name" {
  type = map(string)
  default = {
    dev  = "video-upload-dev"
    test = "video-upload-stage"
    prod = "video-upload-prod"
  }
}

variable "api_stage_name" {
  type    = string
  default = "prod"
}

variable "api_resource_path" {
  type    = string
  default = "test"
}

variable "aws_region" {
  type    = string
  default = "ap-south-1"
}
