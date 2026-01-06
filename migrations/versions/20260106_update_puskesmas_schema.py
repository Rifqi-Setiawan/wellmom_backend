"""Update puskesmas schema to new registration fields/statuses.

- Add latitude/longitude/data_truth_confirmed
- Align registration_status to draft/pending_approval/approved/rejected
- Drop legacy columns removed from the model

Run with: alembic upgrade head
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260106_update_puskesmas"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns
    op.add_column("puskesmas", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("puskesmas", sa.Column("longitude", sa.Float(), nullable=True))
    op.add_column(
        "puskesmas",
        sa.Column(
            "data_truth_confirmed",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )

    # Backfill lat/long from existing geography if present
    op.execute(
        """
        UPDATE puskesmas
        SET latitude = ST_Y(location::geometry),
            longitude = ST_X(location::geometry)
        WHERE location IS NOT NULL;
        """
    )

    # Normalize registration_status values before applying new constraint
    op.execute("ALTER TABLE puskesmas DROP CONSTRAINT IF EXISTS check_puskesmas_status;")
    op.execute(
        "UPDATE puskesmas SET registration_status='pending_approval' WHERE registration_status='pending';"
    )
    op.execute(
        "UPDATE puskesmas SET registration_status='rejected' WHERE registration_status='suspended';"
    )
    op.execute(
        "UPDATE puskesmas SET registration_status='draft' WHERE registration_status IS NULL;"
    )

    # Apply new check constraint
    op.create_check_constraint(
        "check_puskesmas_status",
        "puskesmas",
        "registration_status IN ('draft','pending_approval','approved','rejected')",
    )

    # Drop legacy columns no longer used by the model
    legacy_columns = [
        "code",
        "sk_number",
        "operational_license_number",
        "license_document_url",
        "accreditation_level",
        "accreditation_cert_url",
        "kelurahan",
        "kecamatan",
        "kabupaten",
        "provinsi",
        "postal_code",
        "kepala_sk_number",
        "kepala_sk_document_url",
        "kepala_nik",
        "kepala_ktp_url",
        "kepala_phone",
        "kepala_email",
        "kepala_phone_verified",
        "kepala_email_verified",
        "verification_photo_url",
        "total_perawat",
        "operational_hours",
        "facilities",
        "max_patients",
        "current_patients",
        "suspension_reason",
        "suspended_at",
    ]

    for col in legacy_columns:
        op.execute(f"ALTER TABLE puskesmas DROP COLUMN IF EXISTS {col};")


def downgrade() -> None:
    # Recreate legacy columns (without data) to allow downgrade
    op.add_column("puskesmas", sa.Column("suspended_at", sa.TIMESTAMP(), nullable=True))
    op.add_column("puskesmas", sa.Column("suspension_reason", sa.Text(), nullable=True))
    op.add_column("puskesmas", sa.Column("current_patients", sa.Integer(), nullable=True))
    op.add_column("puskesmas", sa.Column("max_patients", sa.Integer(), nullable=True))
    op.add_column("puskesmas", sa.Column("facilities", sa.Text(), nullable=True))
    op.add_column("puskesmas", sa.Column("operational_hours", sa.Text(), nullable=True))
    op.add_column("puskesmas", sa.Column("total_perawat", sa.Integer(), nullable=True))
    op.add_column("puskesmas", sa.Column("verification_photo_url", sa.String(length=500), nullable=True))
    op.add_column("puskesmas", sa.Column("kepala_email_verified", sa.Boolean(), nullable=True))
    op.add_column("puskesmas", sa.Column("kepala_phone_verified", sa.Boolean(), nullable=True))
    op.add_column("puskesmas", sa.Column("kepala_email", sa.String(length=255), nullable=True))
    op.add_column("puskesmas", sa.Column("kepala_phone", sa.String(length=20), nullable=True))
    op.add_column("puskesmas", sa.Column("kepala_ktp_url", sa.String(length=500), nullable=True))
    op.add_column("puskesmas", sa.Column("kepala_nik", sa.String(length=16), nullable=True))
    op.add_column("puskesmas", sa.Column("kepala_sk_document_url", sa.String(length=500), nullable=True))
    op.add_column("puskesmas", sa.Column("kepala_sk_number", sa.String(length=100), nullable=True))
    op.add_column("puskesmas", sa.Column("postal_code", sa.String(length=5), nullable=True))
    op.add_column("puskesmas", sa.Column("provinsi", sa.String(length=100), nullable=True))
    op.add_column("puskesmas", sa.Column("kabupaten", sa.String(length=100), nullable=True))
    op.add_column("puskesmas", sa.Column("kecamatan", sa.String(length=100), nullable=True))
    op.add_column("puskesmas", sa.Column("kelurahan", sa.String(length=100), nullable=True))
    op.add_column("puskesmas", sa.Column("accreditation_cert_url", sa.String(length=500), nullable=True))
    op.add_column("puskesmas", sa.Column("accreditation_level", sa.String(length=50), nullable=True))
    op.add_column("puskesmas", sa.Column("license_document_url", sa.String(length=500), nullable=True))
    op.add_column("puskesmas", sa.Column("operational_license_number", sa.String(length=100), nullable=True))
    op.add_column("puskesmas", sa.Column("sk_number", sa.String(length=100), nullable=True))
    op.add_column("puskesmas", sa.Column("code", sa.String(length=50), nullable=True))

    # Restore old status constraint
    op.execute("ALTER TABLE puskesmas DROP CONSTRAINT IF EXISTS check_puskesmas_status;")
    op.create_check_constraint(
        "check_puskesmas_status",
        "puskesmas",
        "registration_status IN ('pending','approved','rejected','suspended')",
    )

    # Drop newly added columns
    op.drop_column("puskesmas", "data_truth_confirmed")
    op.drop_column("puskesmas", "longitude")
    op.drop_column("puskesmas", "latitude")
