#!/bin/bash
# Script untuk update constraint jika database di Docker
# Usage: bash update_constraint_docker.sh [container_name] [db_user] [db_name]

CONTAINER_NAME=${1:-wellmom_postgres}
DB_USER=${2:-wellmom}
DB_NAME=${3:-wellmom_db}

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
    echo "Usage: bash update_constraint_docker.sh [container_name] [db_user] [db_name]"
    echo "Default: bash update_constraint_docker.sh wellmom_postgres wellmom wellmom_db"
    exit 1
fi

echo "Menggunakan container: $CONTAINER_NAME"
echo "Database user: $DB_USER"
echo "Database name: $DB_NAME"
echo ""

# Cek apakah file SQL ada
SQL_FILE="migrations/update_user_role_constraint.sql"
if [ ! -f "$SQL_FILE" ]; then
    echo "❌ File SQL tidak ditemukan: $SQL_FILE"
    exit 1
fi

# Jalankan migration
echo "Menjalankan migration..."
docker exec -i $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME < $SQL_FILE

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Migration berhasil!"
    echo ""
    echo "Verifikasi constraint:"
    docker exec -i $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME -c "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'check_user_role';"
else
    echo ""
    echo "❌ Migration gagal!"
    echo ""
    echo "Coba jalankan secara manual:"
    echo "  docker exec -it $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME"
    echo ""
    echo "Kemudian copy-paste SQL berikut:"
    cat $SQL_FILE
    exit 1
fi
