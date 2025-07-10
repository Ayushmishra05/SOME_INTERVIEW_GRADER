
output "ecs_service_name" {
  value = aws_ecs_service.cms_service.name
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.cms_cluster.name
}

output "load_balancer_dns_name" {
  value = aws_lb.cms_lb.dns_name
}
