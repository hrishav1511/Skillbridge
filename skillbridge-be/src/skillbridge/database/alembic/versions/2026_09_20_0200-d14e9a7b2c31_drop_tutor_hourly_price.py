"""Drop hourly_price from tutors and tutor_revisions.

Tutors no longer have an hourly rate; pricing is per service, on the services
table. The column was still being written at registration and read back into
every tutor payload, so the profile and the listings showed a price that meant
nothing and could not be acted on.

DESTRUCTIVE: the stored values are deleted. The downgrade restores the columns
with their default of 0, but the original numbers are not recoverable. Nothing
reads them any more, so they carry no meaning to lose.

Revision ID: d14e9a7b2c31
Revises: c03f5b7e8d90
Create Date: 2026-09-20 02:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d14e9a7b2c31"
down_revision: Union[str, Sequence[str], None] = "c03f5b7e8d90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLES = ("tutors", "tutor_revisions")


def upgrade() -> None:
    for table in TABLES:
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_column("hourly_price")


def downgrade() -> None:
    for table in TABLES:
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "hourly_price",
                    sa.Integer(),
                    nullable=True,
                    server_default="0",
                )
            )
