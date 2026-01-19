#!/bin/bash
# Script untuk update constraint di VPS
# Usage: bash update_constraint_vps.sh

echo "=========================================="
echo "Update User Role Constraint di Database"
echo "=========================================="
echo ""

# Baca environment variables dari .env jika ada
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Extract database info dari DATABASE_URL jika ada
if [ -n "$DATABASE_URL" ]; then
    echo "Menggunakan DATABASE_URL dari environment..."
    # Parse DATABASE_URL: postgresql://user:password@host:port/database
    DB_INFO=$(echo $DATABASE_URL | sed -e 's|postgresql://||' -e 's|@| |' -e 's|:| |' -e 's|/| |')
    DB_USER=$(echo $DB_INFO | awk '{print $1}')
    DB_PASS=$(echo $DB_INFO | awk '{print $2}')
    DB_HOST=$(echo $DB_INFO | awk '{print $3}')
    DB_PORT=$(echo $DB_INFO | awk '{print $4}')
    DB_NAME=$(echo $DB_INFO | awk '{print $5}')
    
    echo "Database: $DB_NAME"
    echo "Host: $DB_HOST"
    echo "Port: ${DB_PORT:-5432}"
    echo ""
    
    # Export PGPASSWORD untuk psql
    export PGPASSWORD=$DB_PASS
    
    # Jalankan migration
    psql -h $DB_HOST -p ${DB_PORT:-5432} -U $DB_USER -d $DB_NAME -f migrations/update_user_role_constraint.sql
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ Migration berhasil!"
        echo ""
        echo "Verifikasi constraint:"
        psql -h $DB_HOST -p ${DB_PORT:-5432} -U $DB_USER -d $DB_NAME -c "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'check_user_role';"
    else
        echo ""
        echo "❌ Migration gagal!"
        exit 1
    fi
else
    echo "DATABASE_URL tidak ditemukan di environment."
    echo ""
    echo "Silakan jalankan SQL secara manual:"
    echo ""
    cat migrations/update_user_role_constraint.sql
    echo ""
    echo "Atau set environment variables:"
    echo "  export PGHOST=your_host"
    echo "  export PGPORT=5432"
    echo "  export PGDATABASE=your_database"
    echo "  export PGUSER=your_username"
    echo "  export PGPASSWORD=your_password"
    echo ""
    echo "Kemudian jalankan:"
    echo "  psql -f migrations/update_user_role_constraint.sql"
fi
