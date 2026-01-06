"""Add user_id column to perawat table."""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260106_add_user_id_to_perawat'
down_revision = '20260106_add_profile_photos'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add user_id column to perawat table and create foreign key constraint."""
    op.add_column(
        'perawat',
        sa.Column('user_id', sa.Integer(), nullable=True)
    )
    op.create_unique_constraint(
        'uq_perawat_user_id',
        'perawat',
        ['user_id']
    )
    op.create_foreign_key(
        'fk_perawat_user_id',
        'perawat',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Remove user_id column from perawat table."""
    op.drop_constraint('fk_perawat_user_id', 'perawat', type_='foreignkey')
    op.drop_constraint('uq_perawat_user_id', 'perawat', type_='unique')
    op.drop_column('perawat', 'user_id')
