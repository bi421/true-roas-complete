#!/bin/bash
# TrueROAS DuckDB Backup Utility
BUCKET_NAME=$1
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

if [ -z "$BUCKET_NAME" ]; then
  echo "Usage: ./backup.sh my-s3-bucket-name"
  exit 1
fi

echo "Backing up DuckDB files to s3://$BUCKET_NAME/backups/$TIMESTAMP/"

aws s3 sync ./data/tenants s3://$BUCKET_NAME/backups/$TIMESTAMP/ \
  --exclude "*" \
  --include "*.duckdb" \
  --storage-class STANDARD_IA

echo "Backup complete. Recommended retention: keep last 30 days of snapshots."