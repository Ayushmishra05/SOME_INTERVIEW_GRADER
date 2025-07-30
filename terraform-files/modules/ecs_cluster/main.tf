
data "aws_vpc" "main" {
  id = var.vpc_id
}

data "aws_subnet" "subnet_a" {
  id = var.subnet_a_id
}

data "aws_subnet" "subnet_b" {
  id = var.subnet_b_id
}

data "aws_subnet" "subnet_c" {
  id = var.subnet_c_id
}

# Data block to check if the policy already exists
data "aws_iam_policy" "ecs_task_execution_policy" {
  name = "ecsTaskExecutionPolicy"
}

# IAM Role for ECS Task Execution
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "ecsTaskExecutionRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action    = "sts:AssumeRole"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Effect    = "Allow"
        Sid       = ""
      }
    ]
  })
}

# Attach the existing policy to the role (if it exists)
resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_attachment" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = data.aws_iam_policy.ecs_task_execution_policy.arn
}

# ECS Task Definition using the execution role ARN
resource "aws_ecs_task_definition" "some_task" {
  family                   = "${local.app_name}-task"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  network_mode             = "awsvpc"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "ARM64"
  }

  container_definitions = jsonencode([
    {
      name      = var.container_name
      image     = var.ecr_image_uri
      essential = true
      portMappings = [{
        containerPort = 80
        protocol      = "tcp"
      }]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "/ecs/${local.app_name}"
          awslogs-region        = var.region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])
}

resource "aws_security_group" "ecs_sg" {
  name        = "${local.app_name}-sg"
  description = "Allow HTTP and HTTPS"
  vpc_id      = data.aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_cloudwatch_log_group" "ecs_logs" {
  name              = "/ecs/${local.app_name}"
  retention_in_days = 7
}


resource "aws_ecs_cluster" "some_cluster" {
  name = var.ClusterName

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}
resource "aws_lb" "some_lb" {
  name               = var.load_balancer #"${local.app_name}-lb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.ecs_sg.id]
  subnets = [
    data.aws_subnet.subnet_a.id,
    data.aws_subnet.subnet_b.id,
    data.aws_subnet.subnet_c.id
  ]
}

resource "aws_lb_target_group" "some_tg" {
  name        = var.target_group
  port        = 80
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.main.id
  target_type = "ip"

  health_check {
    protocol = "HTTP"
    path     = "/"
  }
}

resource "aws_lb_listener" "some_https_listener" {
  load_balancer_arn = aws_lb.some_lb.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  certificate_arn   = var.acm_certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.some_tg.arn
  }
}

resource "aws_ecs_service" "some_service" {
  name            = "${local.app_name}-service"
  cluster         = aws_ecs_cluster.some_cluster.id
  task_definition = aws_ecs_task_definition.some_task.arn
  desired_count   = 1
  launch_type     = "FARGATE"
  platform_version = "LATEST"

  network_configuration {
    subnets = [
      data.aws_subnet.subnet_a.id,
      data.aws_subnet.subnet_b.id,
      data.aws_subnet.subnet_c.id
    ]
    assign_public_ip = true
    security_groups  = [aws_security_group.ecs_sg.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.some_tg.arn
    container_name   = var.container_name
    container_port   = 80
  }

  depends_on = [aws_lb_listener.some_https_listener]
}
resource "aws_appautoscaling_target" "some_scaling_target" {
  max_capacity       = 5
  min_capacity       = 1
  resource_id        = "service/${aws_ecs_cluster.some_cluster.name}/${aws_ecs_service.some_service.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "some_cpu_tracking_policy" {
  name               = "some-cpu-tracking"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.some_scaling_target.resource_id
  scalable_dimension = aws_appautoscaling_target.some_scaling_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.some_scaling_target.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }

    target_value       = 70
    scale_in_cooldown  = 60
    scale_out_cooldown = 30
  }
}

# Step scaling - scale out
resource "aws_cloudwatch_metric_alarm" "some_high_cpu" {
  alarm_name          = "some-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 60
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Scale out if CPU > 80%"
  dimensions = {
    ClusterName  = aws_ecs_cluster.some_cluster.name
    ServiceName  = aws_ecs_service.some_service.name
  }
}

resource "aws_appautoscaling_policy" "step_scale_out" {
  name               = "some-step-scale-out"
  policy_type        = "StepScaling"
  resource_id        = aws_appautoscaling_target.some_scaling_target.resource_id
  scalable_dimension = aws_appautoscaling_target.some_scaling_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.some_scaling_target.service_namespace

  step_scaling_policy_configuration {
    adjustment_type         = "ChangeInCapacity"
    cooldown                = 60
    metric_aggregation_type = "Average"

    step_adjustment {
      metric_interval_lower_bound = 0
      scaling_adjustment          = 1
    }
  }

  depends_on = [aws_cloudwatch_metric_alarm.some_high_cpu]
}

# Step scaling - scale in
resource "aws_cloudwatch_metric_alarm" "some_low_cpu" {
  alarm_name          = "some-low-cpu"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 60
  statistic           = "Average"
  threshold           = 40
  alarm_description   = "Scale in if CPU < 40%"
  dimensions = {
    ClusterName  = aws_ecs_cluster.some_cluster.name
    ServiceName  = aws_ecs_service.some_service.name
  }
}

resource "aws_appautoscaling_policy" "step_scale_in" {
  name               = "some-step-scale-in"
  policy_type        = "StepScaling"
  resource_id        = aws_appautoscaling_target.some_scaling_target.resource_id
  scalable_dimension = aws_appautoscaling_target.some_scaling_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.some_scaling_target.service_namespace

  step_scaling_policy_configuration {
    adjustment_type         = "ChangeInCapacity"
    cooldown                = 60
    metric_aggregation_type = "Average"

    step_adjustment {
      metric_interval_upper_bound = 0
      scaling_adjustment          = -1
    }
  }

  depends_on = [aws_cloudwatch_metric_alarm.some_low_cpu]
}

