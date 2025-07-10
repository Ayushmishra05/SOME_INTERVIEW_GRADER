module "ecr_repo" {
  source = "./modules/ecr"
  repository_name        = lookup(var.ecr_repository_name, terraform.workspace)
  image_tag_mutability   = "MUTABLE"
  scan_on_push           = true
  enable_lifecycle_policy = true
  
  max_image_count        = 10
  tags = {
    Environment = lookup(var.ecr_env_tags, terraform.workspace)
  }
}