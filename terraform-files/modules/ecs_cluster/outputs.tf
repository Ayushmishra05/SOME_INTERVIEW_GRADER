
output "ecs_service_name" {
  value = aws_ecs_service.some_service.name
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.some_cluster.name
}

output "load_balancer_dns_name" {
  value = aws_lb.some_lb.dns_name
}
