#!/usr/bin/env bash
# ==============================================================================
# APAAR-Sutra Encrypted Database Backup Script
# Creates compressed PostgreSQL dump, calculates SHA-256, and encrypts with AES-256.
# RPO (Recovery Point Objective): <= 15 minutes (with automated cron execution)
# RTO (Recovery Time Objective):  <= 30 minutes
# ==============================================================================

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups}"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%SZ")
DB_NAME="${POSTGRES_DB:-apaar_sutra_db}"
DB_USER="${POSTGRES_USER:-apaar_user}"
DB_HOST="${POSTGRES_SERVER:-postgres}"
DB_PORT="${POSTGRES_PORT:-5432}"
BACKUP_PASSPHRASE="${BACKUP_ENCRYPTION_KEY:-apaar_sutra_disaster_recovery_master_key_2026}"

mkdir -p "${BACKUP_DIR}"

RAW_DUMP="${BACKUP_DIR}/dump_${DB_NAME}_${TIMESTAMP}.pgdump"
ENCRYPTED_DUMP="${BACKUP_DIR}/backup_${DB_NAME}_${TIMESTAMP}.pgdump.enc"
CHECKSUM_FILE="${BACKUP_DIR}/backup_${DB_NAME}_${TIMESTAMP}.sha256"

echo "=========================================================="
echo " Starting APAAR-Sutra Encrypted Database Backup: ${TIMESTAMP}"
echo " Database: ${DB_NAME}@${DB_HOST}:${DB_PORT}"
echo "=========================================================="

# 1. Execute pg_dump in custom directory format
echo "[1/4] Dumping PostgreSQL database..."
PGPASSWORD="${POSTGRES_PASSWORD:-apaar_secure_password_2026}" pg_dump \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    -F c \
    -b \
    -v \
    -f "${RAW_DUMP}"

# 2. Compute SHA-256 Checksum over raw dump
echo "[2/4] Generating SHA-256 integrity checksum..."
sha256sum "${RAW_DUMP}" > "${CHECKSUM_FILE}"
cat "${CHECKSUM_FILE}"

# 3. Encrypt dump using OpenSSL AES-256-CBC with PBKDF2
echo "[3/4] Encrypting database archive with AES-256-CBC..."
openssl enc -aes-256-cbc -salt -pbkdf2 -iter 100000 \
    -in "${RAW_DUMP}" \
    -out "${ENCRYPTED_DUMP}" \
    -pass "pass:${BACKUP_PASSPHRASE}"

# 4. Remove unencrypted raw dump
rm -f "${RAW_DUMP}"

echo "[4/4] Backup complete!"
echo " Encrypted Backup File: ${ENCRYPTED_DUMP}"
echo " Checksum File:         ${CHECKSUM_FILE}"
echo " Size: $(du -h "${ENCRYPTED_DUMP}" | cut -f1)"
echo "=========================================================="
