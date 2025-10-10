"""Initial schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2024-10-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('telegram_username', sa.String(), nullable=True),
        sa.Column('first_name', sa.String(), nullable=True),
        sa.Column('last_name', sa.String(), nullable=True),
        sa.Column('timezone', sa.String(), server_default='UTC'),
        sa.Column('digest_enabled', sa.Boolean(), server_default='true'),
        sa.Column('digest_time', sa.String(), server_default='08:00'),
        sa.Column('weekly_digest_enabled', sa.Boolean(), server_default='true'),
        sa.Column('weekly_digest_time', sa.String(), server_default='09:00'),
        sa.Column('google_calendar_enabled', sa.Boolean(), server_default='false'),
        sa.Column('google_calendar_refresh_token', sa.String(), nullable=True),
        sa.Column('caldav_enabled', sa.Boolean(), server_default='false'),
        sa.Column('interaction_patterns', JSONB, server_default='{}'),
        sa.Column('preferences', JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_active_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_telegram_id', 'users', ['telegram_id'], unique=True)
    
    # Create items table
    op.create_table(
        'items',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('original_content', sa.Text(), nullable=True),
        sa.Column('item_type', sa.String(), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('priority', sa.String(), nullable=True),
        sa.Column('tags', JSONB, server_default='[]'),
        sa.Column('counterparties', JSONB, server_default='[]'),
        sa.Column('media_type', sa.String(), nullable=True),
        sa.Column('media_file_id', sa.String(), nullable=True),
        sa.Column('completed', sa.String(), server_default='pending'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_items_id', 'items', ['id'])
    op.create_index('ix_items_user_id', 'items', ['user_id'])
    op.create_index('ix_items_item_type', 'items', ['item_type'])
    op.create_index('ix_items_due_date', 'items', ['due_date'])
    op.create_index('ix_items_completed', 'items', ['completed'])
    op.create_index('ix_items_created_at', 'items', ['created_at'])
    
    # Create embeddings table
    op.create_table(
        'embeddings',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('item_id', sa.BigInteger(), nullable=False),
        sa.Column('embedding', Vector(3072), nullable=False),
        sa.ForeignKeyConstraint(['item_id'], ['items.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_embeddings_id', 'embeddings', ['id'])
    op.create_index('ix_embeddings_item_id', 'embeddings', ['item_id'], unique=True)
    
    # Create tags table
    op.create_table(
        'tags',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('tag_type', sa.String(), server_default='general'),
        sa.Column('usage_count', sa.Integer(), server_default='1'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'name', name='uix_user_tag')
    )
    op.create_index('ix_tags_id', 'tags', ['id'])
    op.create_index('ix_tags_user_id', 'tags', ['user_id'])
    op.create_index('ix_tags_name', 'tags', ['name'])
    
    # Create calendar_events table
    op.create_table(
        'calendar_events',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('external_id', sa.String(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('all_day', sa.Boolean(), server_default='false'),
        sa.Column('status', sa.String(), server_default='confirmed'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('synced_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_calendar_events_id', 'calendar_events', ['id'])
    op.create_index('ix_calendar_events_user_id', 'calendar_events', ['user_id'])
    op.create_index('ix_calendar_events_start_time', 'calendar_events', ['start_time'])
    op.create_index('ix_calendar_events_end_time', 'calendar_events', ['end_time'])
    
    # Create interactions table
    op.create_table(
        'interactions',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('item_id', sa.BigInteger(), nullable=True),
        sa.Column('interaction_type', sa.String(), nullable=False),
        sa.Column('context', JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['item_id'], ['items.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_interactions_id', 'interactions', ['id'])
    op.create_index('ix_interactions_user_id', 'interactions', ['user_id'])
    op.create_index('ix_interactions_item_id', 'interactions', ['item_id'])
    op.create_index('ix_interactions_interaction_type', 'interactions', ['interaction_type'])
    op.create_index('ix_interactions_created_at', 'interactions', ['created_at'])
    
    # Create vector index for embeddings (IVFFlat index for better performance)
    op.execute('CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);')


def downgrade() -> None:
    op.drop_index('ix_interactions_created_at', table_name='interactions')
    op.drop_index('ix_interactions_interaction_type', table_name='interactions')
    op.drop_index('ix_interactions_item_id', table_name='interactions')
    op.drop_index('ix_interactions_user_id', table_name='interactions')
    op.drop_index('ix_interactions_id', table_name='interactions')
    op.drop_table('interactions')
    
    op.drop_index('ix_calendar_events_end_time', table_name='calendar_events')
    op.drop_index('ix_calendar_events_start_time', table_name='calendar_events')
    op.drop_index('ix_calendar_events_user_id', table_name='calendar_events')
    op.drop_index('ix_calendar_events_id', table_name='calendar_events')
    op.drop_table('calendar_events')
    
    op.drop_index('ix_tags_name', table_name='tags')
    op.drop_index('ix_tags_user_id', table_name='tags')
    op.drop_index('ix_tags_id', table_name='tags')
    op.drop_table('tags')
    
    op.drop_index('ix_embeddings_item_id', table_name='embeddings')
    op.drop_index('ix_embeddings_id', table_name='embeddings')
    op.drop_table('embeddings')
    
    op.drop_index('ix_items_created_at', table_name='items')
    op.drop_index('ix_items_completed', table_name='items')
    op.drop_index('ix_items_due_date', table_name='items')
    op.drop_index('ix_items_item_type', table_name='items')
    op.drop_index('ix_items_user_id', table_name='items')
    op.drop_index('ix_items_id', table_name='items')
    op.drop_table('items')
    
    op.drop_index('ix_users_telegram_id', table_name='users')
    op.drop_index('ix_users_id', table_name='users')
    op.drop_table('users')

