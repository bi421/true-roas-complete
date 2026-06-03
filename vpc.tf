module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "trueroas-vpc-${terraform.workspace}"
  cidr = var.vpc_cidr

  azs             = ["${var.aws_region}a", "${var.aws_region}b"]
  private_subnets = var.private_subnets
  public_subnets  = var.public_subnets

  enable_nat_gateway = true
  single_nat_gateway = terraform.workspace != "prod"

  enable_dns_hostnames = true
  enable_dns_support   = true

  # Database and Cache Subnet Groups
  create_database_subnet_group    = true
  create_elasticache_subnet_group = true

  database_subnets    = var.database_subnets
  elasticache_subnets = var.elasticache_subnets
}