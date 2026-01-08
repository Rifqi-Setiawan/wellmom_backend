"""
Script to run database migration for updating user role constraint.
Run this script to update the check_user_role constraint in the database.
"""

import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import engine
from app.config import settings


def run_migration():
    """Run the migration to update user role constraint."""
    print("Starting migration: Update user role constraint...")
    print(f"Database URL: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'hidden'}")
    
    # Read SQL migration file
    migration_file = Path(__file__).parent / "update_user_role_constraint.sql"
    
    if not migration_file.exists():
        print(f"Error: Migration file not found: {migration_file}")
        return False
    
    with open(migration_file, 'r') as f:
        sql_commands = f.read()
    
    # Parse SQL commands (split by semicolon, filter comments)
    lines = sql_commands.split('\n')
    commands = []
    current_command = []
    
    for line in lines:
        stripped = line.strip()
        # Skip empty lines and full-line comments
        if not stripped or stripped.startswith('--'):
            continue
        # Remove inline comments
        if '--' in stripped:
            stripped = stripped.split('--')[0].strip()
        # If line ends with semicolon, it's the end of a command
        if stripped.endswith(';'):
            current_command.append(stripped.rstrip(';').strip())
            if current_command:
                full_command = ' '.join(current_command)
                if full_command:
                    commands.append(full_command)
            current_command = []
        else:
            current_command.append(stripped)
    
    # Add any remaining command
    if current_command:
        full_command = ' '.join(current_command)
        if full_command:
            commands.append(full_command)
    
    try:
        with engine.connect() as conn:
            # Begin transaction
            trans = conn.begin()
            try:
                for command in commands:
                    if command:
                        print(f"Executing: {command[:80]}...")
                        conn.execute(text(command))
                
                # Commit transaction
                trans.commit()
                print("✅ Migration completed successfully!")
                print("\nConstraint 'check_user_role' has been updated.")
                print("Allowed roles: super_admin, puskesmas, perawat, ibu_hamil, kerabat")
                return True
                
            except Exception as e:
                trans.rollback()
                print(f"❌ Error during migration: {e}")
                raise
                
    except Exception as e:
        print(f"❌ Failed to run migration: {e}")
        return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
