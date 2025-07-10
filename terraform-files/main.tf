terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket               = "boopathy-devsecops-engineer"
    key                  = "terraform.tfstate"
    workspace_key_prefix = "SOME"
    region               = "ap-south-1"
    encrypt              = true
    use_lockfile         = true
  }
}

provider "aws" {
  region = "ap-south-1"
}