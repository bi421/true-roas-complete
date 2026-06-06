provider "aws" {
  region = "us-east-1"
}

# --- Variables ---
variable "db_password" {
  description = "RDS Root Password"
  type        = string
  sensitive   = true
}

# --- Security Groups ---

resource "aws_security_group" "trueroas_sg" {
  name        = "trueroas-production-sg"
  description = "Allow inbound traffic for TrueROAS API"

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

resource "aws_security_group" "rds_sg" {
  name        = "trueroas-rds-sg"
  description = "Allow inbound traffic for PostgreSQL"

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.trueroas_sg.id] # Only allow access from the API server
  }
}

# --- S3 Bucket for Audit Reports ---

resource "aws_s3_bucket" "reports_bucket" {
  bucket = "trueroas-audit-reports-${random_id.bucket_suffix.hex}" # Unique name

  tags = {
    Name        = "TrueROAS Reports"
    Environment = "Production"
  }
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket_versioning" "reports_versioning" {
  bucket = aws_s3_bucket.reports_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "reports_encryption" {
  bucket = aws_s3_bucket.reports_bucket.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "reports_block_public" {
  bucket = aws_s3_bucket.reports_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# --- RDS PostgreSQL Instance ---

resource "aws_db_instance" "trueroas_db" {
  identifier             = "trueroas-metadata-prod"
  instance_class         = "db.t3.micro" # Suitable size for MVP
  allocated_storage      = 20
  engine                 = "postgres"
  engine_version         = "15.3"
  username               = "trueroas_admin"
  password               = var.db_password
  db_name                = "trueroas"
  
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  multi_az               = true  # High Availability
  storage_encrypted      = true # Security
  skip_final_snapshot    = true  # Recommended true for dev/test, false for production
  
  backup_retention_period = 7
  publicly_accessible     = false # Not accessible from the internet
}

# --- EC2 Instance ---

resource "aws_instance" "app_server" {
  ami           = "ami-0c55b159cbfafe1f0" # Ubuntu 22.04 LTS
  instance_type = "t3.medium"
  security_groups = [aws_security_group.trueroas_sg.name]

  tags = {
    Name = "TrueROAS-Production-API"
  }
}