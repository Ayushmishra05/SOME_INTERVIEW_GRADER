module "ecs" {
  source = "./modules/ecs_cluster"

  vpc_id              = var.vpc_id[var.environment]
  subnet_a_id         = var.subnet_a_id[var.environment]
  subnet_b_id         = var.subnet_b_id[var.environment]
  subnet_c_id         = var.subnet_c_id[var.environment]
  ecr_image_uri       = module.ecr_repo.ecr_image_uri
  acm_certificate_arn = "arn:aws:acm:ap-south-1:066208711325:certificate/4655ae80-1467-4db8-8cee-a8e822407f4f"
  min_capacity        = var.min_capacity[var.environment]
  max_capacity        = var.max_capacity[var.environment]
  load_balancer       = var.load_balancer[var.environment]
  target_group        = var.target_group[var.environment]
  ClusterName         = var.ClusterName[var.environment]
}
output "deployed_image_uri" {
  value = module.ecr_repo.ecr_image_uri
}