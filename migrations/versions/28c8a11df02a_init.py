"""init

Revision ID: 28c8a11df02a
Revises: da6bb745997d
Create Date: 2024-04-02 16:31:57.621007

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28c8a11df02a'
down_revision: Union[str, None] = 'da6bb745997d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user_session', sa.Column('is_active', sa.Boolean(), nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user_session', 'is_active')
    # ### end Alembic commands ###