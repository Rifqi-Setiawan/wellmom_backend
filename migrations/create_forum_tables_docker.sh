#!/bin/bash

# Script untuk menjalankan migration create_forum_tables.sql di Docker container
# Usage: bash migrations/create_forum_tables_docker.sh

set -e

echo "=========================================="
echo "Create Forum Tables Migration"
echo "=========================================="
echo ""

# Default values (sesuaikan dengan setup Anda)
CONTAINER_NAME="${POSTGRES_CONTAINER:-wellmom_postgres}"
DB_USER="${DB_USER:-wellmom}"
DB_NAME="${DB_NAME:-wellmom_db}"

echo "Menggunakan konfigurasi:"
echo "Container: $CONTAINER_NAME"
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo ""

# Check if container exists
if ! docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "❌ Container '$CONTAINER_NAME' tidak ditemukan!"
    echo ""
    echo "Cek container yang tersedia:"
    docker ps -a --format 'table {{.Names}}\t{{.Status}}'
    exit 1
fi

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "⚠️  Container '$CONTAINER_NAME' tidak berjalan. Mencoba start..."
    docker start $CONTAINER_NAME
    sleep 2
fi

echo "Menjalankan migration..."
echo ""

# Run migration
if docker exec -i $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME < migrations/create_forum_tables.sql; then
    echo ""
    echo "✅ Migration berhasil!"
    echo ""
    echo "Verifikasi tables:"
    docker exec -i $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME -c "\dt posts post_likes post_replies"
else
    echo ""
    echo "❌ Migration gagal!"
    exit 1
fi
