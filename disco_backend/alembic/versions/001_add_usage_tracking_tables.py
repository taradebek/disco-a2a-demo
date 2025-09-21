"""Add usage tracking tables

Revision ID: 001_usage_tracking
Revises: 
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_usage_tracking'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create enums
    payment_status_enum = postgresql.ENUM(
        'pending', 'processing', 'completed', 'failed', 'cancelled', 'refunded',
        name='payment_status_enum'
    )
    payment_status_enum.create(op.get_bind())

    payment_method_enum = postgresql.ENUM(
        'crypto', name='payment_method_enum'
    )
    payment_method_enum.create(op.get_bind())

    currency_enum = postgresql.ENUM(
        'ETH', 'USDC', 'BTC', name='currency_enum'
    )
    currency_enum.create(op.get_bind())

    network_enum = postgresql.ENUM(
        'ethereum', 'polygon', 'arbitrum', 'solana', name='network_enum'
    )
    network_enum.create(op.get_bind())

    # Create api_keys table
    op.create_table('api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key_id', sa.String(length=255), nullable=False),
        sa.Column('key_hash', sa.String(length=255), nullable=False),
        sa.Column('environment', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('permissions', sa.JSON(), nullable=False, default={}),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('request_count', sa.Integer(), nullable=False, default=0),
        sa.Column('user_email', sa.String(length=255), nullable=True),
        sa.Column('organization', sa.String(length=255), nullable=True),
        sa.Column('user_metadata', sa.JSON(), nullable=False, default={}),
        sa.Column('rate_limit_per_hour', sa.Integer(), nullable=False, default=1000),
        sa.Column('monthly_quota', sa.Integer(), nullable=True),
        sa.Column('current_month_usage', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_api_keys_key_id', 'api_keys', ['key_id'], unique=True)

    # Create agents table
    op.create_table('agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', sa.String(length=255), nullable=False),
        sa.Column('api_key_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('capabilities', sa.JSON(), nullable=False, default={}),
        sa.Column('wallet_address', sa.String(length=255), nullable=False),
        sa.Column('supported_currencies', sa.JSON(), nullable=False, default={}),
        sa.Column('supported_networks', sa.JSON(), nullable=False, default={}),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['api_key_id'], ['api_keys.id'])
    )
    op.create_index('ix_agents_agent_id', 'agents', ['agent_id'], unique=True)
    op.create_index('ix_agents_wallet_address', 'agents', ['wallet_address'])

    # Create services table
    op.create_table('services',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('service_id', sa.String(length=255), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('currency', currency_enum, nullable=False),
        sa.Column('network', network_enum, nullable=False),
        sa.Column('x402_endpoint', sa.String(length=500), nullable=False),
        sa.Column('payment_method', payment_method_enum, nullable=False, default='crypto'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('metadata', sa.JSON(), nullable=False, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'])
    )
    op.create_index('ix_services_service_id', 'services', ['service_id'], unique=True)

    # Create wallets table
    op.create_table('wallets',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('wallet_id', sa.String(length=255), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('address', sa.String(length=255), nullable=False),
        sa.Column('network', network_enum, nullable=False),
        sa.Column('wallet_type', sa.String(length=50), nullable=False, default='hot'),
        sa.Column('is_multisig', sa.Boolean(), nullable=False, default=False),
        sa.Column('required_signatures', sa.Integer(), nullable=True, default=1),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('metadata', sa.JSON(), nullable=False, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'])
    )
    op.create_index('ix_wallets_wallet_id', 'wallets', ['wallet_id'], unique=True)
    op.create_index('ix_wallets_address', 'wallets', ['address'])

    # Create wallet_balances table
    op.create_table('wallet_balances',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('wallet_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('currency', currency_enum, nullable=False),
        sa.Column('balance', sa.Float(), nullable=False, default=0.0),
        sa.Column('reserved', sa.Float(), nullable=False, default=0.0),
        sa.Column('available', sa.Float(), nullable=False, default=0.0),
        sa.Column('last_updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('last_sync_block', sa.Integer(), nullable=True, default=0),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['wallet_id'], ['wallets.id'])
    )
    op.create_index('idx_wallet_currency', 'wallet_balances', ['wallet_id', 'currency'], unique=True)

    # Create payments table
    op.create_table('payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payment_id', sa.String(length=255), nullable=False),
        sa.Column('from_agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('to_agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', currency_enum, nullable=False),
        sa.Column('network', network_enum, nullable=False),
        sa.Column('method', payment_method_enum, nullable=False, default='crypto'),
        sa.Column('disco_fee', sa.Float(), nullable=False, default=0.0),
        sa.Column('disco_fee_percentage_amount', sa.Float(), nullable=False, default=0.0),
        sa.Column('disco_fee_fixed_amount', sa.Float(), nullable=False, default=0.0),
        sa.Column('disco_fee_percentage', sa.Float(), nullable=False, default=0.029),
        sa.Column('disco_fee_fixed', sa.Float(), nullable=False, default=0.30),
        sa.Column('net_amount', sa.Float(), nullable=False),
        sa.Column('status', payment_status_enum, nullable=False, default='pending'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('reference', sa.String(length=255), nullable=True),
        sa.Column('transaction_hash', sa.String(length=255), nullable=True),
        sa.Column('block_number', sa.Integer(), nullable=True),
        sa.Column('gas_used', sa.Integer(), nullable=True),
        sa.Column('gas_price', sa.Float(), nullable=True),
        sa.Column('x402_payment_id', sa.String(length=255), nullable=True),
        sa.Column('x402_signature', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False, default={}),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['from_agent_id'], ['agents.id']),
        sa.ForeignKeyConstraint(['to_agent_id'], ['agents.id'])
    )
    op.create_index('ix_payments_payment_id', 'payments', ['payment_id'], unique=True)
    op.create_index('ix_payments_transaction_hash', 'payments', ['transaction_hash'])
    op.create_index('idx_payment_status', 'payments', ['status'])
    op.create_index('idx_payment_created_at', 'payments', ['created_at'])
    op.create_index('idx_payment_agents', 'payments', ['from_agent_id', 'to_agent_id'])

    # Create transactions table
    op.create_table('transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transaction_id', sa.String(length=255), nullable=False),
        sa.Column('hash', sa.String(length=255), nullable=False),
        sa.Column('network', network_enum, nullable=False),
        sa.Column('block_number', sa.Integer(), nullable=True),
        sa.Column('block_hash', sa.String(length=255), nullable=True),
        sa.Column('transaction_index', sa.Integer(), nullable=True),
        sa.Column('from_address', sa.String(length=255), nullable=False),
        sa.Column('to_address', sa.String(length=255), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('gas_limit', sa.Integer(), nullable=False),
        sa.Column('gas_used', sa.Integer(), nullable=True),
        sa.Column('gas_price', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, default='pending'),
        sa.Column('confirmations', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False, default={}),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_transactions_transaction_id', 'transactions', ['transaction_id'], unique=True)
    op.create_index('ix_transactions_hash', 'transactions', ['hash'], unique=True)
    op.create_index('idx_transaction_network', 'transactions', ['network'])
    op.create_index('idx_transaction_addresses', 'transactions', ['from_address', 'to_address'])
    op.create_index('idx_transaction_status', 'transactions', ['status'])

    # Create webhook_events table
    op.create_table('webhook_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_id', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=False),
        sa.Column('resource_id', sa.String(length=255), nullable=False),
        sa.Column('webhook_url', sa.String(length=500), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, default='pending'),
        sa.Column('attempts', sa.Integer(), nullable=False, default=0),
        sa.Column('max_attempts', sa.Integer(), nullable=False, default=3),
        sa.Column('response_status', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_webhook_events_event_id', 'webhook_events', ['event_id'], unique=True)
    op.create_index('ix_webhook_events_event_type', 'webhook_events', ['event_type'])
    op.create_index('ix_webhook_events_resource_id', 'webhook_events', ['resource_id'])
    op.create_index('idx_webhook_status', 'webhook_events', ['status'])
    op.create_index('idx_webhook_scheduled', 'webhook_events', ['scheduled_at'])
    op.create_index('idx_webhook_resource', 'webhook_events', ['resource_type', 'resource_id'])

    # Create audit_logs table (NEW for usage tracking)
    op.create_table('audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('api_key_id', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('resource_id', sa.String(length=255), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('sdk_version', sa.String(length=50), nullable=True),
        sa.Column('environment', sa.String(length=50), nullable=True),
        sa.Column('details', sa.JSON(), nullable=False, default={}),
        sa.Column('success', sa.Boolean(), nullable=False, default=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_event_type', 'audit_logs', ['event_type'])
    op.create_index('idx_audit_api_key', 'audit_logs', ['api_key_id'])
    op.create_index('idx_audit_timestamp', 'audit_logs', ['created_at'])
    op.create_index('idx_audit_user', 'audit_logs', ['user_id'])

    # Create usage_statistics table (NEW for usage tracking)
    op.create_table('usage_statistics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('api_key_id', sa.String(length=255), nullable=False),
        sa.Column('date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_type', sa.String(length=20), nullable=False),
        sa.Column('total_requests', sa.Integer(), nullable=False, default=0),
        sa.Column('unique_agents', sa.Integer(), nullable=False, default=0),
        sa.Column('total_payments', sa.Integer(), nullable=False, default=0),
        sa.Column('payment_volume', sa.Float(), nullable=False, default=0.0),
        sa.Column('fees_collected', sa.Float(), nullable=False, default=0.0),
        sa.Column('services_created', sa.Integer(), nullable=False, default=0),
        sa.Column('services_consumed', sa.Integer(), nullable=False, default=0),
        sa.Column('error_count', sa.Integer(), nullable=False, default=0),
        sa.Column('error_rate', sa.Float(), nullable=False, default=0.0),
        sa.Column('metadata', sa.JSON(), nullable=False, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_usage_api_key_date', 'usage_statistics', ['api_key_id', 'date'])
    op.create_index('idx_usage_period', 'usage_statistics', ['period_type', 'date'])


def downgrade():
    # Drop tables in reverse order
    op.drop_table('usage_statistics')
    op.drop_table('audit_logs')
    op.drop_table('webhook_events')
    op.drop_table('transactions')
    op.drop_table('payments')
    op.drop_table('wallet_balances')
    op.drop_table('wallets')
    op.drop_table('services')
    op.drop_table('agents')
    op.drop_table('api_keys')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS network_enum')
    op.execute('DROP TYPE IF EXISTS currency_enum')
    op.execute('DROP TYPE IF EXISTS payment_method_enum')
    op.execute('DROP TYPE IF EXISTS payment_status_enum') 