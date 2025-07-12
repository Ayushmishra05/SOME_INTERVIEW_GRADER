terraform {
  required_providers {
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.2.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket               = "some-prod2025"
    key                  = "lambda.tfstate"
    workspace_key_prefix = "terraform_files"
    region               = "ap-south-1"
    encrypt              = true
    use_lockfile         = true
  }
}

provider "aws" {
  region = "ap-south-1"
}