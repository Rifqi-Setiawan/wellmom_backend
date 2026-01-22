"""
Script to run database migration for updating health_records table structure.
Run this script to update the health_records table with new columns and constraints.
"""

import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import engine
from app.config import settings


def run_migration():
    """Run the migration to update health_records table."""
    print("Starting migration: Update health_records table structure...")
    print(f"Database URL: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'hidden'}")

    # Read SQL migration file
    migration_file = Path(__file__).parent / "update_health_records_table.sql"

    if not migration_file.exists():
        print(f"Error: Migration file not found: {migration_file}")
        return False

    with open(migration_file, 'r') as f:
        sql_content = f.read()

    # Parse SQL commands (handle multi-line commands and DO blocks)
    commands = []
    current_command = []
    in_do_block = False

    for line in sql_content.split('\n'):
        stripped = line.strip()

        # Skip empty lines and full-line comments
        if not stripped or stripped.startswith('--'):
            continue

        # Check for DO block start
        if stripped.upper().startswith('DO $$') or stripped.upper().startswith('DO'):
            in_do_block = True

        current_command.append(line)

        # Check for DO block end or regular command end
        if in_do_block:
            if '$$;' in stripped:
                commands.append('\n'.join(current_command))
                current_command = []
                in_do_block = False
        elif stripped.endswith(';'):
            commands.append('\n'.join(current_command))
            current_command = []

    # Add any remaining command
    if current_command:
        commands.append('\n'.join(current_command))

    try:
        with engine.connect() as conn:
            # Begin transaction
            trans = conn.begin()
            try:
                for i, command in enumerate(commands, 1):
                    command = command.strip()
                    if command:
                        # Get first line for display (truncated)
                        first_line = command.split('\n')[0][:80]
                        print(f"[{i}/{len(commands)}] Executing: {first_line}...")
                        conn.execute(text(command))

                # Commit transaction
                trans.commit()
                print("\n" + "=" * 60)
                print("Migration completed successfully!")
                print("=" * 60)
                print("\nChanges applied to health_records table:")
                print("  - Added/verified: checked_by (perawat/mandiri)")
                print("  - Added/verified: weight, complaints")
                print("  - Added/verified: hemoglobin, blood_glucose, protein_urin")
                print("  - Added/verified: upper_arm_circumference, fundal_height, fetal_heart_rate")
                print("  - Removed: checkup_type, supplements, treatment_plan, physical_examination")
                print("  - Removed: referral_needed, next_checkup_date, next_checkup_notes")
                print("  - Removed: diagnosis, data_source, medications, referral_notes")
                return True

            except Exception as e:
                trans.rollback()
                print(f"\nError during migration: {e}")
                raise

    except Exception as e:
        print(f"\nFailed to run migration: {e}")
        return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
