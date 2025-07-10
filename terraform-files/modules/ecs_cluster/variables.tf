variable "vpc_id" {}
variable "subnet_a_id" {}
variable "subnet_b_id" {}
variable "subnet_c_id" {}
variable "ecr_image_uri" {}
variable "acm_certificate_arn" {}

variable "task_execution_role_name" {
  default = "ecsTaskExecutionRole"
}

# variable "app_name" {
#   default = "cms-web-app"
# }
variable "app_name" {
  description = "Full app name. Leave null to auto-generate."
  type        = string
  default     = null
}

locals {
  app_name = (
    var.app_name != null    
    ? var.app_name
    : "cms-web-app-${terraform.workspace}"
  )
}
variable "region" {
  default = "ap-south-1"
}

variable "container_name" {
  default = "cms-web-repo"
}

variable "cpu" {
  default = "1024"
}

variable "memory" {
  default = "3072"
}


variable "min_capacity" {
}

variable "max_capacity" {
}

variable "load_balancer" {
  
}
variable "target_group" {
  
}
variable "ClusterName" {
  
}