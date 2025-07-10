variable "ecr_repository_name" {
  type = map(string)
  default = {
    "dev"  = "dev-some-api-repo"
    "test" = "test-some-api-repo"
    "prod" = "prod-some-api-repo"
  }
}

#ecr repo tags
variable "ecr_env_tags" {
  type = map(string)
  default = {
    "dev"  = "dev"
    "test" = "test"
    "prod" = "prod"
  }
  
}




variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "test", "prod"], var.environment)
    error_message = "Must be dev, test, or prod"
  }
}

#vpc for ecs
variable "vpc_id" {
  type = map(string)
  default = {
    dev  = "vpc-0fdfeb5211f65fba3"
    test = "vpc-0d3f7fc807218d15b"
    prod = "vpc-0d3f7fc807218d15b"
  }
}


#subnet for ecs 
variable "subnet_a_id" {
  type = map(string)
  default = {
    dev  = "subnet-0aadfdf71a3d77311"
    test = "subnet-0adcb03cea7476613"
    prod = "subnet-0ac9b6ee245d3e9eb"
  }
}

variable "subnet_b_id" {
  type = map(string)
  default = {
    dev  = "subnet-08ddb013211397efd"
    test = "subnet-00fe2bd0c30a0efd5"
    prod = "subnet-00fe2bd0c30a0efd5"
  }
}


variable "subnet_c_id" {
  type = map(string)
  default = {
    dev  = "subnet-05784a9291af39212"
    test = "subnet-0ac9b6ee245d3e9eb"
    prod = "subnet-0adcb03cea7476613"
  }
}


#minimum capacity for ecs scaling
variable "min_capacity" {
    type = map(number)
  default = {
    
    dev  = 1
    test = 1
    prod =1
  }
}

#maximum capacity for ecs scaling

variable "max_capacity" {
    type = map(number)
  default = {
    
    dev  = 2
    test =  2
    prod = 2
  }
}



variable "load_balancer"{
      type = map(string)
  default = {
    
    dev  = "dev-load-balance"
    test =  "test-load-balance"
    prod = "prod-load-balance"
  }
}



variable "target_group"{
          type = map(string)
  default = {
    
    dev  = "dev-tg"
    test =  "test-tg"
    prod = "prod-tg"
  }
}


variable "ClusterName" {
    type = map(string)
  default = {
    
    dev  = "some-cluster-dev"
    test =  "some-cluster-test"
    prod = "some-cluster-prod"
  }
}
