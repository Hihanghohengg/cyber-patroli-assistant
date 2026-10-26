"""Add intelligence and dashboard tables.

Revision ID: 001_intelligence
Revises: 
Create Date: 2026-10-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_intelligence'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. issue_clusters
    op.create_table(
        'issue_clusters',
        sa.Column('issue_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('canonical_name', sa.String(length=500), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), server_default='Lainnya'),
        sa.Column('keywords', postgresql.JSONB(astext_type=sa.Text()), server_default='[]'),
        sa.Column('hashtags', postgresql.JSONB(astext_type=sa.Text()), server_default='[]'),
        sa.Column('named_entities', postgresql.JSONB(astext_type=sa.Text()), server_default='[]'),
        sa.Column('status', sa.String(length=50), server_default='ACTIVE'),
        sa.Column('first_seen_at', sa.DateTime(), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_issue_clusters_category', 'issue_clusters', ['category'])
    op.create_index('ix_issue_clusters_status', 'issue_clusters', ['status'])
    op.create_index('ix_issue_clusters_first_seen', 'issue_clusters', ['first_seen_at'])
    op.create_index('ix_issue_clusters_last_seen', 'issue_clusters', ['last_seen_at'])

    # 2. issue_contents
    op.create_table(
        'issue_contents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('issue_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('issue_clusters.issue_id', ondelete='CASCADE'), nullable=False),
        sa.Column('content_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('contents.content_id', ondelete='CASCADE'), nullable=False),
        sa.Column('similarity_score', sa.Float(), server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('issue_id', 'content_id', name='uq_issue_content')
    )
    op.create_index('ix_issue_contents_issue_id', 'issue_contents', ['issue_id'])
    op.create_index('ix_issue_contents_content_id', 'issue_contents', ['content_id'])

    # 3. topic_snapshots
    op.create_table(
        'topic_snapshots',
        sa.Column('snapshot_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('issue_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('issue_clusters.issue_id', ondelete='CASCADE'), nullable=False),
        sa.Column('snapshot_time', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('content_count', sa.Integer(), server_default='0'),
        sa.Column('unique_sources', sa.Integer(), server_default='0'),
        sa.Column('platform_count', sa.Integer(), server_default='0'),
        sa.Column('growth_rate', sa.Float(), server_default='0.0'),
        sa.Column('velocity', sa.Float(), server_default='0.0'),
        sa.Column('trending_score', sa.Float(), server_default='0.0'),
        sa.Column('platform_distribution', postgresql.JSONB(astext_type=sa.Text()), server_default='{}'),
        sa.Column('sentiment_distribution', postgresql.JSONB(astext_type=sa.Text()), server_default='{}'),
    )
    op.create_index('ix_topic_snapshots_issue_id', 'topic_snapshots', ['issue_id'])
    op.create_index('ix_topic_snapshots_time', 'topic_snapshots', ['snapshot_time'])

    # 4. content_analyses
    op.create_table(
        'content_analyses',
        sa.Column('analysis_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('content_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('contents.content_id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('what', sa.Text(), nullable=True),
        sa.Column('who', sa.Text(), nullable=True),
        sa.Column('when_info', sa.Text(), nullable=True),
        sa.Column('where_info', sa.Text(), nullable=True),
        sa.Column('why', sa.Text(), nullable=True),
        sa.Column('how', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('main_topic', sa.String(length=300), nullable=True),
        sa.Column('sub_topics', postgresql.JSONB(astext_type=sa.Text()), server_default='[]'),
        sa.Column('keywords', postgresql.JSONB(astext_type=sa.Text()), server_default='[]'),
        sa.Column('hashtags', postgresql.JSONB(astext_type=sa.Text()), server_default='[]'),
        sa.Column('named_entities', postgresql.JSONB(astext_type=sa.Text()), server_default='[]'),
        sa.Column('sentiment', sa.String(length=50), nullable=True),
        sa.Column('tone', sa.String(length=100), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('relevance_score', sa.Float(), server_default='0.0'),
        sa.Column('urgency_score', sa.Float(), server_default='0.0'),
        sa.Column('confidence_score', sa.Float(), server_default='0.0'),
        sa.Column('misinfo_indicators', postgresql.JSONB(astext_type=sa.Text()), server_default='[]'),
        sa.Column('analysis_model', sa.String(length=100), nullable=True),
        sa.Column('analysis_status', sa.String(length=50), server_default='COMPLETED'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_content_analyses_content_id', 'content_analyses', ['content_id'])
    op.create_index('ix_content_analyses_main_topic', 'content_analyses', ['main_topic'])
    op.create_index('ix_content_analyses_category', 'content_analyses', ['category'])
    op.create_index('ix_content_analyses_sentiment', 'content_analyses', ['sentiment'])

    # 5. dashboard_users
    op.create_table(
        'dashboard_users',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('username', sa.String(length=100), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('role', sa.String(length=50), server_default='ANALYST'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('telegram_id', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('dashboard_users')
    op.drop_table('content_analyses')
    op.drop_table('topic_snapshots')
    op.drop_table('issue_contents')
    op.drop_table('issue_clusters')
