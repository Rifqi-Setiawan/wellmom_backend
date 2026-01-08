#!/bin/bash
# Script untuk update constraint jika database di Docker
# Usage: bash update_constraint_docker.sh [container_name]

CONTAINER_NAME=${1:-postgres}

echo "=========================================="
echo "Update User Role Constraint (Docker)"
echo "=========================================="
echo ""

# Cek apakah container ada
if ! docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "❌ Container '$CONTAINER_NAME' tidak ditemukan!"
    echo ""
    echo "Container yang tersedia:"
    docker ps -a --format '{{.Names}}'
    echo ""
    echo "Usage: bash update_constraint_docker.sh [container_name]"
    exit 1
fi

echo "Menggunakan container: $CONTAINER_NAME"
echo ""

# Copy SQL file ke container dan jalankan
echo "Menjalankan migration..."
docker exec -i $CONTAINER_NAME psql -U postgres -d wellmom < migrations/update_user_role_constraint.sql

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Migration berhasil!"
    echo ""
    echo "Verifikasi constraint:"
    docker exec -i $CONTAINER_NAME psql -U postgres -d wellmom -c "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'check_user_role';"
else
    echo ""
    echo "❌ Migration gagal!"
    echo ""
    echo "Coba jalankan secara manual:"
    echo "  docker exec -it $CONTAINER_NAME psql -U postgres -d wellmom"
    echo ""
    echo "Kemudian copy-paste SQL berikut:"
    cat migrations/update_user_role_constraint.sql
    exit 1
fi
