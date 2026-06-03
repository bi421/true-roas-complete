# RDS PostgreSQL (Multi-AZ)
resource "aws_db_instance" "postgres" {
  identifier            = "trueroas-metadata-${terraform.workspace}"
  engine               = "postgres"
  engine_version       = "15.3"
  instance_class       = var.rds_instance_class
  allocated_storage    = 20
  db_name              = "trueroas"
  username             = "trueroas_admin"
  password             = data.aws_secretsmanager_secret_version.db_password.secret_string
  
  db_subnet_group_name   = module.vpc.database_subnet_group_name
  vpc_security_group_ids = [aws_security_group.rds.id]
  
  multi_az               = true
  storage_encrypted      = true
  skip_final_snapshot    = terraform.workspace != "prod"
  backup_retention_period = 7
}

# ElastiCache Redis (Cluster Mode Enabled)
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id          = "trueroas-redis-${terraform.workspace}"
  replication_group_description = "Redis cluster for Celery and Caching"
  node_type                     = var.redis_node_type
  port                          = 6379
  parameter_group_name          = "default.redis7.cluster.on"
  automatic_failover_enabled    = true
  
  num_node_groups         = var.redis_node_groups
  replicas_per_node_group = 1

  subnet_group_name  = module.vpc.elasticache_subnet_group_name
  security_group_ids = [aws_security_group.redis.id]
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
}

resource "aws_s3_bucket" "audit_archive" {
  bucket = "trueroas-audit-archive-${terraform.workspace}-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_versioning" "archive_versioning" {
  bucket = aws_s3_bucket.audit_archive.id
  versioning_configuration { status = "Enabled" }
}