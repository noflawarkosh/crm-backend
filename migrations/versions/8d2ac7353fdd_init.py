"""init

Revision ID: 8d2ac7353fdd
Revises: a7818d095307
Create Date: 2024-05-17 16:32:47.127716

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8d2ac7353fdd'
down_revision: Union[str, None] = 'a7818d095307'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('products_product', 'media_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('products_product', 'media_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    # ### end Alembic commands ###
