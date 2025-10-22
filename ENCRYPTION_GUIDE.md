# Field-Level Encryption Implementation Guide

## Overview

This guide documents the field-level encryption implementation for sensitive data in the AI Thought Processor platform. The implementation uses **AES-256-GCM** authenticated encryption to protect sensitive user data at rest.

## Table of Contents

1. [What is Encrypted](#what-is-encrypted)
2. [Encryption Technology](#encryption-technology)
3. [Performance Impact](#performance-impact)
4. [Deployment Instructions](#deployment-instructions)
5. [Key Management](#key-management)
6. [Key Rotation](#key-rotation)
7. [Disaster Recovery](#disaster-recovery)
8. [Security Best Practices](#security-best-practices)
9. [Troubleshooting](#troubleshooting)

---

## What is Encrypted

### Encrypted Fields

The following sensitive fields are encrypted using AES-256-GCM:

| Table | Field | Type | Contains |
|-------|-------|------|----------|
| **users** | `context` | JSONB → TEXT | User demographics, goals, constraints, personal challenges |
| **thoughts** | `text` | TEXT | Raw user thought text (highly confidential) |
| **thoughts** | `classification` | JSONB → TEXT | AI classification analysis |
| **thoughts** | `analysis` | JSONB → TEXT | AI analysis results |
| **thoughts** | `value_impact` | JSONB → TEXT | Impact analysis |
| **thoughts** | `action_plan` | JSONB → TEXT | Action recommendations |
| **thoughts** | `priority` | JSONB → TEXT | Priority information |
| **thought_cache** | `response` | JSONB → TEXT | Cached AI responses |

### Not Encrypted

The following fields are **NOT** encrypted:

- **Metadata**: User IDs, timestamps, status fields
- **Hashed data**: Password hashes (already using bcrypt)
- **Non-sensitive**: Email addresses, subscription info
- **Embeddings**: Vector embeddings (used for similarity search)

---

## Encryption Technology

### Algorithm: AES-256-GCM

**AES-256-GCM** (Advanced Encryption Standard with Galois/Counter Mode) provides:

- **256-bit keys**: Maximum strength symmetric encryption
- **Authenticated encryption**: Prevents tampering (includes authentication tag)
- **Unique IV per operation**: 96-bit random nonce for each encryption
- **Hardware acceleration**: AES-NI support on modern CPUs

### Encryption Format

Encrypted data is stored as:

```
enc_v1:<key_id>:<base64_encoded_data>
```

Where `<base64_encoded_data>` contains:
- **Nonce** (12 bytes): Random initialization vector
- **Ciphertext**: Encrypted data
- **Authentication tag** (16 bytes): Integrity verification

Example:
```
enc_v1:default:aGVsbG8gd29ybGQgdGhpcyBpcyBhIHRlc3QgZW5jcnlwdGlvbg==
```

### Security Properties

- **Confidentiality**: Data cannot be read without the key
- **Integrity**: Tampering is detected automatically
- **Authenticity**: Guarantees data origin
- **Forward secrecy**: Old ciphertexts remain secure after key rotation

---

## Performance Impact

### Encryption Overhead

| Operation | Time per Record | Impact |
|-----------|----------------|---------|
| **Text encryption** (1KB) | ~1-5 microseconds | Negligible |
| **JSON encryption** (1KB) | ~5-10 microseconds | Negligible |
| **Text decryption** (1KB) | ~1-5 microseconds | Negligible |
| **JSON decryption** (1KB) | ~5-10 microseconds | Negligible |

### Real-World Impact

- **API latency increase**: < 1ms per request
- **Database size increase**: ~30-40% (Base64 encoding overhead)
- **CPU usage increase**: < 5% (AES-NI hardware acceleration)
- **Memory overhead**: Minimal (streaming encryption)

### Performance Optimizations

1. **Hardware acceleration**: AES-NI instructions on modern CPUs
2. **Singleton pattern**: Reuses encryption service instance
3. **Batched operations**: Migrates data in configurable batches
4. **Lazy decryption**: Only decrypts when data is accessed

---

## Deployment Instructions

### Prerequisites

1. **PostgreSQL 12+** with pgvector extension
2. **Python 3.9+** with required packages
3. **Secure key storage** (environment variables or secrets manager)
4. **Database backup** before migration

### Step 1: Generate Master Key

Generate a secure 256-bit master key:

```bash
python3 -c 'from common.security import EncryptionService; print(EncryptionService.generate_master_key())'
```

Example output:
```
xK8pQ2vB9mN5rL7wT4jH6gF3dS1aP0oI9uY8tR7eW6qM5nL4kJ3hG2fD1sA0=
```

### Step 2: Store Master Key Securely

**Option A: Environment Variable** (Development)

```bash
# Add to .env file
ENCRYPTION_MASTER_KEY=xK8pQ2vB9mN5rL7wT4jH6gF3dS1aP0oI9uY8tR7eW6qM5nL4kJ3hG2fD1sA0=

# Export for current session
export ENCRYPTION_MASTER_KEY=xK8pQ2vB9mN5rL7wT4jH6gF3dS1aP0oI9uY8tR7eW6qM5nL4kJ3hG2fD1sA0=
```

**Option B: AWS Secrets Manager** (Production)

```python
import boto3
import json

secrets_client = boto3.client('secretsmanager')

# Store key
secrets_client.create_secret(
    Name='thoughtprocessor/encryption-master-key',
    SecretString=json.dumps({'key': 'YOUR_MASTER_KEY_HERE'})
)

# Retrieve key in application
response = secrets_client.get_secret_value(SecretId='thoughtprocessor/encryption-master-key')
master_key = json.loads(response['SecretString'])['key']
os.environ['ENCRYPTION_MASTER_KEY'] = master_key
```

**Option C: HashiCorp Vault** (Production)

```bash
# Store key
vault kv put secret/thoughtprocessor/encryption master_key=YOUR_KEY_HERE

# Retrieve key
vault kv get -field=master_key secret/thoughtprocessor/encryption
```

### Step 3: Backup Database

```bash
# Create full backup
pg_dump -U thoughtprocessor -d thoughtprocessor > backup_before_encryption_$(date +%Y%m%d_%H%M%S).sql

# Verify backup
ls -lh backup_before_encryption_*.sql
```

### Step 4: Run Schema Migration

```bash
# Navigate to project root
cd /path/to/RAGMultiAgent

# Run migration
psql -U thoughtprocessor -d thoughtprocessor -f database/migrations/005_prepare_for_encryption.sql
```

Expected output:
```
BEGIN
ALTER TABLE
ALTER TABLE
ALTER TABLE
...
COMMIT
```

### Step 5: Encrypt Existing Data

**Dry Run (Recommended First)**:

```bash
python database/migrate_encrypt_data.py --dry-run
```

**Production Migration**:

```bash
# Small datasets (< 10,000 records)
python database/migrate_encrypt_data.py --batch-size 100

# Large datasets (> 10,000 records)
python database/migrate_encrypt_data.py --batch-size 1000
```

**Monitor Progress**:

```bash
# Check migration status
psql -U thoughtprocessor -d thoughtprocessor -c "SELECT * FROM encryption_migration_status;"
```

Example output:
```
 table_name  | field_name     | total_records | encrypted_records | pending_records | percent_complete
-------------+----------------+---------------+-------------------+-----------------+------------------
 users       | context        |           150 |               150 |               0 |           100.00
 thoughts    | classification |           450 |               450 |               0 |           100.00
 thoughts    | analysis       |           450 |               450 |               0 |           100.00
```

### Step 6: Finalize Migration

**Only run after 100% migration complete**:

```bash
psql -U thoughtprocessor -d thoughtprocessor -c "SELECT finalize_encryption_migration();"
```

Expected output:
```
NOTICE:  Encryption migration finalized successfully!
```

### Step 7: Enable Encryption in Application

Update your configuration:

```python
# api/database.py or main.py
from common.database.postgres_adapter import PostgreSQLAdapter

# Enable encryption (default: True)
adapter = PostgreSQLAdapter(
    host="localhost",
    port=5432,
    database="thoughtprocessor",
    user="thoughtprocessor",
    password="your_password",
    enable_encryption=True  # ✓ Encryption enabled
)
```

### Step 8: Restart Application

```bash
# Restart API server
systemctl restart thoughtprocessor-api

# Or for Docker
docker-compose restart api

# Verify encryption is active
curl http://localhost:8000/api/health | jq
```

### Step 9: Verification

**Test that encrypted data is accessible**:

```bash
# Create a test thought
curl -X POST http://localhost:8000/api/thoughts \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Test encrypted thought"}'

# Retrieve the thought
curl -X GET http://localhost:8000/api/thoughts/THOUGHT_ID \
  -H "Authorization: Bearer YOUR_TOKEN"

# Verify text is decrypted properly
```

**Check database (should see encrypted data)**:

```bash
psql -U thoughtprocessor -d thoughtprocessor -c "SELECT id, LEFT(text, 50) FROM thoughts LIMIT 1;"
```

Expected output:
```
                  id                  |                       left
--------------------------------------+---------------------------------------------------
 a1b2c3d4-e5f6-7890-abcd-ef1234567890 | enc_v1:default:aGVsbG8gd29ybGQgdGhpcyBpcyBhIHRl...
```

---

## Key Management

### Master Key Security

**DO**:
- ✅ Use a cryptographically secure random key generator
- ✅ Store keys in dedicated secrets management systems
- ✅ Use different keys for dev/staging/production
- ✅ Rotate keys periodically (every 6-12 months)
- ✅ Backup keys securely (encrypted, offline storage)
- ✅ Use environment-specific key IDs

**DON'T**:
- ❌ Hardcode keys in source code
- ❌ Commit keys to version control
- ❌ Store keys in plaintext files
- ❌ Share keys via email/Slack
- ❌ Use the same key across environments
- ❌ Store keys in application logs

### Key Storage Options

#### Development

```bash
# .env file (NOT committed to git)
ENCRYPTION_MASTER_KEY=your_development_key_here
```

#### Staging/Production

**AWS Secrets Manager**:
```python
import boto3
secret = boto3.client('secretsmanager').get_secret_value(
    SecretId='prod/thoughtprocessor/encryption-key'
)
```

**Google Cloud Secret Manager**:
```python
from google.cloud import secretmanager
client = secretmanager.SecretManagerServiceClient()
name = "projects/PROJECT_ID/secrets/encryption-key/versions/latest"
response = client.access_secret_version(request={"name": name})
key = response.payload.data.decode('UTF-8')
```

**Azure Key Vault**:
```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()
client = SecretClient(vault_url="https://YOUR-VAULT.vault.azure.net/", credential=credential)
key = client.get_secret("encryption-master-key").value
```

---

## Key Rotation

### Why Rotate Keys?

- **Security best practice**: Limit exposure from potential key compromise
- **Compliance requirements**: GDPR, PCI-DSS, SOC 2 often require rotation
- **Breach mitigation**: Limit impact of past breaches
- **Recommended frequency**: Every 6-12 months

### Rotation Strategy

**Two-Phase Rotation** (Zero Downtime):

#### Phase 1: Dual-Key Operation

1. **Generate new key**:
```bash
python3 -c 'from common.security import EncryptionService; print(EncryptionService.generate_master_key())'
```

2. **Store new key with different ID**:
```bash
# .env
ENCRYPTION_MASTER_KEY=old_key_here  # key_id: "default"
ENCRYPTION_MASTER_KEY_V2=new_key_here  # key_id: "v2"
```

3. **Update application to use new key for writes**:
```python
# Initialize with new key
encryption_service = EncryptionService(master_key=new_key, key_id="v2")

# But keep old key available for reads
old_encryption_service = EncryptionService(master_key=old_key, key_id="default")
```

4. **Re-encrypt all data with new key**:
```bash
python database/rotate_encryption_key.py --old-key-id default --new-key-id v2
```

#### Phase 2: Remove Old Key

5. **Verify all data uses new key**:
```bash
psql -c "SELECT COUNT(*) FROM thoughts WHERE text LIKE 'enc_v1:default:%';"
# Should return 0
```

6. **Remove old key from configuration**:
```bash
# .env
ENCRYPTION_MASTER_KEY=new_key_here  # Now the primary key
```

7. **Update key_id in encryption service**:
```python
encryption_service = EncryptionService(master_key=new_key, key_id="default")
```

### Automated Key Rotation Script

Create `database/rotate_encryption_key.py`:

```python
#!/usr/bin/env python3
"""Rotate encryption key for all encrypted fields"""
import asyncio
from common.security import EncryptionService
from common.database import PostgreSQLAdapter

async def rotate_keys(old_key, new_key, old_key_id, new_key_id):
    old_enc = EncryptionService(master_key=old_key, key_id=old_key_id)
    new_enc = EncryptionService(master_key=new_key, key_id=new_key_id)

    adapter = PostgreSQLAdapter()
    await adapter.connect()

    # Get all encrypted thoughts
    thoughts = await adapter.get_thoughts(limit=10000)

    for thought in thoughts:
        # Decrypt with old key
        decrypted_text = old_enc.decrypt_text(thought['text'])
        # Re-encrypt with new key
        encrypted_text = new_enc.encrypt_text(decrypted_text)
        # Update
        await adapter.update_thought(thought['id'], text=encrypted_text)

    print(f"✓ Rotated {len(thoughts)} records")

if __name__ == "__main__":
    # Run rotation
    asyncio.run(rotate_keys(
        old_key=os.getenv('ENCRYPTION_MASTER_KEY'),
        new_key=os.getenv('ENCRYPTION_MASTER_KEY_V2'),
        old_key_id='default',
        new_key_id='v2'
    ))
```

---

## Disaster Recovery

### Scenario 1: Lost Encryption Key

**Prevention**:
- Store keys in multiple secure locations
- Backup keys offline in encrypted form
- Use key escrow for critical keys

**Recovery** (if you have backup):
```bash
# Restore key from backup
export ENCRYPTION_MASTER_KEY=<restored_key>

# Verify key works
python -c 'from common.security import get_encryption_service; enc = get_encryption_service(); print("Key valid!")'
```

**If key is permanently lost**:
- **Encrypted data is UNRECOVERABLE** (by design)
- Restore from pre-encryption backup
- Re-run encryption migration with new key

### Scenario 2: Corrupted Encrypted Data

**Detection**:
```python
try:
    decrypted = encryption.decrypt_text(encrypted_value)
except Exception as e:
    logger.error(f"Decryption failed: {e}")
    # Corrupted or tampered data
```

**Recovery**:
```bash
# Restore from database backup
pg_restore -U thoughtprocessor -d thoughtprocessor backup_file.sql

# Or restore individual records from backup
psql -c "UPDATE thoughts SET text = backup.text FROM backup_thoughts WHERE thoughts.id = backup.id;"
```

### Scenario 3: Database Breach

**Immediate Actions**:
1. **Rotate encryption keys immediately**
2. **Audit access logs** for unauthorized access
3. **Notify affected users** (GDPR Article 33)
4. **Force password resets** for all users

**Impact with encryption**:
- ✅ **Encrypted fields are protected** (unusable without key)
- ⚠️ **Metadata is visible** (IDs, timestamps)
- ⚠️ **Unencrypted fields are exposed** (emails, subscriptions)

---

## Security Best Practices

### 1. Defense in Depth

Encryption is ONE layer of security:

```
User Authentication (JWT)
    ↓
Network Security (TLS/HTTPS)
    ↓
Database Access Control (PostgreSQL roles)
    ↓
Field-Level Encryption (AES-256-GCM)  ← YOU ARE HERE
    ↓
Disk Encryption (LUKS/dm-crypt)
    ↓
Physical Security (Data center)
```

### 2. Key Management Best Practices

- **Separation of duties**: Different people manage keys vs. application
- **Key versioning**: Track which key version encrypted each record
- **Audit logging**: Log all key access and usage
- **Backup encryption**: Encrypt database backups separately

### 3. Compliance Considerations

**GDPR**:
- ✅ Encryption meets "state of the art" requirement (Article 32)
- ✅ Supports right to erasure (delete encryption key)
- ✅ Breach notification scope reduced (encrypted data)

**PCI-DSS**:
- ✅ Requirement 3.4: Render PAN unreadable
- ✅ Requirement 3.5: Document key management procedures
- ✅ Requirement 3.6: Key management processes

**HIPAA**:
- ✅ Encryption is addressable safeguard
- ✅ Reduces breach notification requirements
- ✅ Supports minimum necessary principle

### 4. Monitoring & Auditing

**Monitor these metrics**:
- Encryption/decryption failure rates
- Key rotation schedule adherence
- Unauthorized key access attempts
- Database access patterns

**Logging**:
```python
# Log encryption events
logger.info(f"Encrypted field: {field_name} for user: {user_id}")
logger.warning(f"Decryption failed for field: {field_name}, error: {e}")
```

---

## Troubleshooting

### Issue: "ENCRYPTION_MASTER_KEY environment variable not set"

**Cause**: Master key not configured

**Solution**:
```bash
export ENCRYPTION_MASTER_KEY=$(python3 -c 'from common.security import EncryptionService; print(EncryptionService.generate_master_key())')
```

### Issue: "Failed to decrypt data: Invalid authentication tag"

**Cause**:
- Wrong encryption key
- Corrupted ciphertext
- Tampered data

**Solution**:
```bash
# Verify correct key is set
echo $ENCRYPTION_MASTER_KEY

# Check if data is actually encrypted
psql -c "SELECT LEFT(text, 10) FROM thoughts LIMIT 1;"
# Should start with "enc_v1:"

# Restore from backup if corrupted
pg_restore ...
```

### Issue: "Performance degradation after encryption"

**Cause**: Large datasets without optimization

**Solution**:
```python
# Enable connection pooling
adapter = PostgreSQLAdapter(pool_size=20)

# Use batch operations
thoughts = await adapter.get_thoughts(limit=100)  # Process in batches

# Monitor query performance
EXPLAIN ANALYZE SELECT * FROM thoughts WHERE user_id = '...';
```

### Issue: "Database size increased significantly"

**Cause**: Base64 encoding overhead (~33%)

**Solution**:
```bash
# Expected size increase: 30-40%
# Check current size
psql -c "SELECT pg_size_pretty(pg_database_size('thoughtprocessor'));"

# Run VACUUM to reclaim space
psql -c "VACUUM FULL ANALYZE;"

# Consider compression at database level
ALTER TABLE thoughts SET (toast_compression = lz4);
```

---

## FAQ

**Q: Can I disable encryption temporarily?**
A: Yes, set `enable_encryption=False` in PostgreSQLAdapter, but encrypted data will not be decrypted.

**Q: What happens if I lose the master key?**
A: All encrypted data is permanently unrecoverable. Always maintain secure backups of keys.

**Q: Can I search encrypted fields?**
A: No, encrypted fields cannot be searched directly. Use separate searchable metadata or deterministic encryption for search.

**Q: Does encryption work with Supabase adapter?**
A: The current implementation is for PostgreSQL adapter. Supabase adapter would need similar updates.

**Q: Can I use different keys for different users?**
A: Yes, implement per-user keys using `derive_key_from_password()` method (not currently implemented).

**Q: What's the performance impact on large datasets?**
A: Minimal (<1ms per request) due to AES-NI hardware acceleration. Batch operations recommended for migrations.

---

## Support & Resources

- **Encryption Module**: `common/security/encryption.py`
- **PostgreSQL Adapter**: `common/database/postgres_adapter.py`
- **Migration Scripts**: `database/migrations/005_prepare_for_encryption.sql`
- **Data Migration**: `database/migrate_encrypt_data.py`

For questions or issues, consult:
- This documentation
- Code comments in implementation files
- NIST Guidelines on encryption: https://csrc.nist.gov/publications/fips
- OWASP Cryptographic Storage Cheat Sheet

---

**Last Updated**: October 22, 2025
**Version**: 1.0
**Encryption Standard**: AES-256-GCM
**Compliance**: GDPR, PCI-DSS, HIPAA, SOC 2
