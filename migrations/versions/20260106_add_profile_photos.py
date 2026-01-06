"""Add profile photo fields to perawat and ibu_hamil tables.

Adds profile_photo_url column to both tables for storing profile photo URLs.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260106_add_profile_photos"
down_revision = "20260106_update_puskesmas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add profile_photo_url to perawat table
    op.add_column(
        "perawat",
        sa.Column(
            "profile_photo_url",
            sa.String(length=500),
            nullable=True,
        ),
    )

    # Add profile_photo_url to ibu_hamil table
    op.add_column(
        "ibu_hamil",
        sa.Column(
            "profile_photo_url",
            sa.String(length=500),
            nullable=True,
        ),
    )


def downgrade() -> None:
    # Drop profile_photo_url from ibu_hamil table
    op.drop_column("ibu_hamil", "profile_photo_url")

    # Drop profile_photo_url from perawat table
    op.drop_column("perawat", "profile_photo_url")
