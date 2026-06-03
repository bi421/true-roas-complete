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