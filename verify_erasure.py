#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

import sys
import subprocess
import redis
from pathlib import Path
from src.trueroas.core.config import settings

def verify_subject_purge(subject_hash: str):
    """
    Requirement 3: Verification Protocol.
    Scans binary files and caches for residuals.
    """
    print(f"🕵️  Forensic Audit for Subject Hash: {subject_hash}")
    findings = 0

    # 1. Binary Scan of SQLite files
    data_dir = Path("./data/tenants")
    # Requirement 3 & WAL Recovery: Check all related sqlite files (.db, .db-wal, .db-shm)
    for db_file in data_dir.glob("*.db*"):
        # Use grep -a to search raw binary for the hash string
        res = subprocess.run(["grep", "-a", subject_hash, str(db_file)], capture_output=True)
        if res.returncode == 0:
            print(f"❌ FINDING: Residual hash found in binary file: {db_file}")
            findings += 1

    # 2. Redis Keyspace Scan
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    keys = r.keys(f"*{subject_hash}*")
    if keys:
        print(f"❌ FINDING: Redis keys containing hash detected: {keys}")
        findings += 1

    # 3. Log Scan (Simulated)
    # In production, this would use the ELK/CloudWatch API
    
    if findings == 0:
        print("✅ VERIFIED: No residuals found in primary storage or cache.")
        return True
    else:
        print(f"🚨 FAILURE: {findings} residual data points identified.")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_erasure.py <subject_hash>")
        sys.exit(1)
    
    success = verify_subject_purge(sys.argv[1])
    sys.exit(0 if success else 1)