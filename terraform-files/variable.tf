variable "ecr_repository_name" {
  type = map(string)
  default = {
    "dev"  = "dev-some-api-repo"
    "test" = "test-some-api-repo"
    "prod" = "prod-some-api-repo"
  }
}

variable "ecr_env_tags" {
  type = map(string)
  default = {
    "dev"  = "dev"
    "test" = "test"
    "prod" = "prod"
  }
  
}