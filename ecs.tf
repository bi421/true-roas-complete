resource "aws_ecs_cluster" "main" {
  name = "trueroas-cluster-${terraform.workspace}"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# Task Definition for FastAPI App
resource "aws_ecs_task_definition" "api" {
  family                   = "trueroas-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 1024
  memory                   = 2048
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name  = "api"
      image = "${var.ecr_repository}:latest"
      portMappings = [{ containerPort = 8001 }]
      environment = [
        { name = "DATABASE_TYPE", value = "postgres" },
        { name = "REDIS_URL", value = "rediss://${aws_elasticache_replication_group.redis.configuration_endpoint_address}:6379/0" }
      ]
      secrets = [
        { name = "APP_SECRET_SALT", valueFrom = aws_secretsmanager_secret.app_salt.arn },
        { name = "POSTGRES_URL", valueFrom = aws_secretsmanager_secret.db_url.arn }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/trueroas-api"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "api"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "api" {
  name            = "trueroas-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_count
  launch_type     = "FARGATE"
  # Network configuration, ALB target groups, etc.
}