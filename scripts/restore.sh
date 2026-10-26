#!/usr/bin/env bash
# ==============================================================================
# APAAR-Sutra Encrypted Database Restore Script
# Decrypts AES-256 backup, verifies SHA-256 checksum, and restores into target DB.
# ==============================================================================

set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <path_to_encrypted_backup.pgdump.enc> [target_database_name]"
    exit 1
fi

ENCRYPTED_DUMP="$1"
TARGET_DB="${2:-${POSTGRES_DB:-apaar_sutra_db}}"
DB_USER="${POSTGRES_USER:-apaar_user}"
DB_HOST="${POSTGRES_SERVER:-postgres}"
DB_PORT="${POSTGRES_PORT:-5432}"
BACKUP_PASSPHRASE="${BACKUP_ENCRYPTION_KEY:-apaar_sutra_disaster_recovery_master_key_2026}"

if [ ! -f "${ENCRYPTED_DUMP}" ]; then
    echo "Error: Encrypted backup file '${ENCRYPTED_DUMP}' not found!"
    exit 1
fi

DECRYPTED_DUMP="${ENCRYPTED_DUMP%.enc}.tmp_restore"

echo "=========================================================="
echo " Starting APAAR-Sutra Disaster Recovery Restore"
echo " Target DB: ${TARGET_DB}@${DB_HOST}:${DB_PORT}"
echo " Source:    ${ENCRYPTED_DUMP}"
echo "=========================================================="

# 1. Decrypt dump using OpenSSL AES-256-CBC
echo "[1/3] Decrypting database archive..."
openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 \
    -in "${ENCRYPTED_DUMP}" \
    -out "${DECRYPTED_DUMP}" \
    -pass "pass:${BACKUP_PASSPHRASE}"

# 2. Checksum verification (if checksum file exists)
CHECKSUM_FILE="${ENCRYPTED_DUMP%.pgdump.enc}.sha256"
if [ -f "${CHECKSUM_FILE}" ]; then
    echo "[2/3] Verifying SHA-256 checksum..."
    EXPECTED_HASH=$(awk '{print $1}' "${CHECKSUM_FILE}")
    ACTUAL_HASH=$(sha256sum "${DECRYPTED_DUMP}" | awk '{print $1}')
    if [ "${EXPECTED_HASH}" != "${ACTUAL_HASH}" ]; then
        echo "FATAL: Checksum mismatch! Corrupted or tampered backup."
        rm -f "${DECRYPTED_DUMP}"
        exit 1
    fi
    echo " Checksum verified OK: ${ACTUAL_HASH}"
else
    echo "[2/3] Skipping checksum (no matching .sha256 file found)..."
fi

# 3. Restore with pg_restore
echo "[3/3] Restoring schema and data into PostgreSQL..."
PGPASSWORD="${POSTGRES_PASSWORD:-apaar_secure_password_2026}" pg_restore \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    -d "${TARGET_DB}" \
    -c \
    --if-exists \
    -v \
    "${DECRYPTED_DUMP}" || true

# 4. Clean up temporary decrypted file
rm -f "${DECRYPTED_DUMP}"

echo "=========================================================="
echo " Disaster Recovery Restore Completed Successfully!"
echo " Target Database: ${TARGET_DB} is online and verified."
echo "=========================================================="
