"""Add RAG knowledge base and entity normalization tables (PRD v2).

Revision ID: 002_rag_entities
Revises: 001_intelligence
Create Date: 2026-10-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = sa.Text

# revision identifiers, used by Alembic.
revision = '002_rag_entities'
down_revision = '001_intelligence'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Enable pgvector extension if postgres
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2. entities
    op.create_table(
        'entities',
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('canonical_name', sa.String(length=255), nullable=False),
        sa.Column('source_kind', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('entity_type', 'canonical_name', name='uq_entity_type_canonical')
    )
    op.create_index('ix_entities_type_status', 'entities', ['entity_type', 'status'])
    op.create_index('ix_entities_canonical', 'entities', ['canonical_name'])

    # 3. entity_aliases
    op.create_table(
        'entity_aliases',
        sa.Column('alias_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('entities.entity_id', ondelete='CASCADE'), nullable=False),
        sa.Column('alias_text', sa.String(length=255), nullable=False),
        sa.Column('alias_normalized', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_entity_aliases_normalized', 'entity_aliases', ['alias_normalized'])
    op.create_index('ix_entity_aliases_entity_id', 'entity_aliases', ['entity_id'])

    # 4. report_actors
    op.create_table(
        'report_actors',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('reports.report_id', ondelete='CASCADE'), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('entities.entity_id', ondelete='CASCADE'), nullable=False),
        sa.Column('role_description', sa.String(length=100), server_default='TARGET'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_report_actors_report_id', 'report_actors', ['report_id'])
    op.create_index('ix_report_actors_entity_id', 'report_actors', ['entity_id'])

    # 5. Alter reports to add PRD v2 fields
    op.add_column('reports', sa.Column('ai_topic_raw', sa.String(length=255), nullable=True))
    op.add_column('reports', sa.Column('ai_actors_raw', postgresql.JSONB(astext_type=sa.Text()), server_default='[]'))
    op.add_column('reports', sa.Column('ai_source_raw', sa.String(length=255), nullable=True))
    op.add_column('reports', sa.Column('ai_source_type', sa.String(length=50), nullable=True))
    op.add_column('reports', sa.Column('topic_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('entities.entity_id'), nullable=True))
    op.add_column('reports', sa.Column('source_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('entities.entity_id'), nullable=True))
    op.add_column('reports', sa.Column('analyst_notes', sa.Text(), nullable=True))

    # 6. knowledge_entries
    op.create_table(
        'knowledge_entries',
        sa.Column('entry_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('reports.report_id', ondelete='CASCADE'), nullable=False),
        sa.Column('decision', sa.String(length=50), nullable=False),
        sa.Column('final_label', sa.String(length=100), nullable=False),
        sa.Column('final_risk', sa.String(length=50), nullable=False),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('analyst_notes', sa.Text(), nullable=True),
        sa.Column('summary_text', sa.Text(), nullable=True),
        sa.Column('topic_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('entities.entity_id'), nullable=True),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('entities.entity_id'), nullable=True),
        sa.Column('embed_text', sa.Text(), nullable=True),
        sa.Column('embedding', Vector(768) if hasattr(Vector, '__call__') else sa.Text(), nullable=True),
        sa.Column('decided_by', sa.BigInteger(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('deactivated_by', sa.BigInteger(), nullable=True),
        sa.Column('deactivated_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_knowledge_entries_report_id', 'knowledge_entries', ['report_id'])
    op.create_index('ix_knowledge_entries_active', 'knowledge_entries', ['is_active'])
    op.create_index('ix_knowledge_entries_decision', 'knowledge_entries', ['decision'])
    op.create_index('ix_knowledge_entries_final_label', 'knowledge_entries', ['final_label'])


def downgrade() -> None:
    op.drop_table('knowledge_entries')
    op.drop_column('reports', 'analyst_notes')
    op.drop_column('reports', 'source_id')
    op.drop_column('reports', 'topic_id')
    op.drop_column('reports', 'ai_source_type')
    op.drop_column('reports', 'ai_source_raw')
    op.drop_column('reports', 'ai_actors_raw')
    op.drop_column('reports', 'ai_topic_raw')
    op.drop_table('report_actors')
    op.drop_table('entity_aliases')
    op.drop_table('entities')
