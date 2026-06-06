terraform {
  required_version = ">= 1.5.0"

  backend "s3" {
    bucket         = "trueroas-terraform-state"
    key            = "environments/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "trueroas-terraform-locks"
    encrypt        = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "TrueROAS"
      Environment = terraform.workspace
      ManagedBy   = "Terraform"
    }
  }
}

# I-001 Correction: Implementing real compute and database resources
resource "aws_db_instance" "trueroas_db" {
  identifier             = "trueroas-postgres-prod"
  instance_class         = "db.t3.micro"
  allocated_storage      = 20
  engine                 = "postgres"
  engine_version         = "15.3"
  username               = "trueroas_admin"
  password               = var.db_password
  db_name                = "trueroas_central"
  
  vpc_security_group_ids = [module.vpc.database_security_group_id]
  db_subnet_group_name   = module.vpc.database_subnet_group_name
  multi_az               = true
  storage_encrypted      = true
  skip_final_snapshot    = true
}

resource "aws_ecs_cluster" "trueroas_cluster" {
  name = "trueroas-production-cluster"
}

resource "aws_ecs_service" "api_service" {
  name            = "trueroas-api"
  cluster         = aws_ecs_cluster.trueroas_cluster.id
  task_definition = aws_ecs_task_definition.api_task.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = module.vpc.private_subnets
    security_groups  = [aws_security_group.api_sg.id]
    assign_public_ip = false
  }
}

resource "aws_security_group" "api_sg" {
  name        = "trueroas-api-sg"
  description = "Allow inbound traffic for TrueROAS API"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 8001
    to_port     = 8001
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

resource "aws_ecs_task_definition" "api_task" {
  family                   = "trueroas-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"

  container_definitions = jsonencode([
    {
      name      = "trueroas-api"
      image     = "trueroas-api:latest"
      essential = true
      portMappings = [
        {
          containerPort = 8001
          hostPort      = 8001
        }
      ]
    }
  ])
}

variable "db_password" {
  type      = string
  sensitive = true
}