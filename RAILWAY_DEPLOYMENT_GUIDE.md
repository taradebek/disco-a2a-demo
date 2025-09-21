# Railway Deployment Guide - Disco SDK Usage Tracking

## Overview

This guide covers deploying the Disco SDK usage tracking system on Railway, including all required database tables and configurations.

## 🗄️ Required Database Tables

The usage tracking system requires **12 tables** to be created in your PostgreSQL database:

### Core Tables (9)
1. **`api_keys`** - User authentication and identification
2. **`agents`** - AI agents registered in the system  
3. **`services`** - Services offered by agents
4. **`wallets`** - Agent cryptocurrency wallets
5. **`wallet_balances`** - Real-time wallet balances
6. **`payments`** - Payment transactions
7. **`transactions`** - Blockchain transaction records
8. **`webhook_events`** - External webhook notifications

### Usage Tracking Tables (2) - NEW
9. **`audit_logs`** - Comprehensive usage and event tracking
10. **`usage_statistics`** - Aggregated analytics data

### Supporting Enums (4)
- `payment_status_enum` - Payment statuses
- `payment_method_enum` - Payment methods
- `currency_enum` - Supported currencies
- `network_enum` - Blockchain networks

## 🚀 Railway Deployment Steps

### Step 1: Database Setup

#### Option A: Using Alembic Migration (Recommended)
```bash
# In your Railway environment
cd disco_backend
alembic upgrade head
```

#### Option B: Manual SQL Execution
If Alembic isn't set up, you can run the SQL directly in Railway's database console:

```sql
-- Create enums first
CREATE TYPE payment_status_enum AS ENUM ('pending', 'processing', 'completed', 'failed', 'cancelled', 'refunded');
CREATE TYPE payment_method_enum AS ENUM ('crypto');
CREATE TYPE currency_enum AS ENUM ('ETH', 'USDC', 'BTC');
CREATE TYPE network_enum AS ENUM ('ethereum', 'polygon', 'arbitrum', 'solana');

-- Then create tables (see full SQL below)
```

### Step 2: Environment Variables

Add these to your Railway environment variables:

```bash
# Database
DATABASE_URL=postgresql://username:password@host:port/database

# Disco Configuration
DISCO_ENVIRONMENT=production
DISCO_API_BASE_URL=https://your-railway-app.railway.app
DISCO_SECRET_KEY=your-secret-key-here

# Analytics Configuration
ENABLE_USAGE_TRACKING=true
ANALYTICS_RETENTION_DAYS=90
MAX_AUDIT_LOGS_PER_USER=10000

# Optional: External Services
WEBHOOK_SECRET=your-webhook-secret
RATE_LIMIT_REDIS_URL=redis://your-redis-url
```

### Step 3: Update Railway Configuration

#### railway.toml
```toml
[build]
builder = "NIXPACKS"
buildCommand = "pip install -r requirements.txt"

[deploy]
startCommand = "alembic upgrade head && python main.py"
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3

[[services]]
name = "disco-backend"
source = "disco_backend"

[services.variables]
PORT = "8000"
```

### Step 4: Update Main Application

Add the analytics router to your main FastAPI app:

```python
# disco_backend/main.py
from fastapi import FastAPI
from disco_backend.api import analytics, users

app = FastAPI(title="Disco API", version="1.0.0")

# Add routers
app.include_router(analytics.router)
app.include_router(users.router)

# Add other existing routers...
```

## 📋 Complete Database Schema

### Core Tables SQL

<details>
<summary>Click to expand full SQL schema</summary>

```sql
-- Create UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create enums
CREATE TYPE payment_status_enum AS ENUM ('pending', 'processing', 'completed', 'failed', 'cancelled', 'refunded');
CREATE TYPE payment_method_enum AS ENUM ('crypto');
CREATE TYPE currency_enum AS ENUM ('ETH', 'USDC', 'BTC');
CREATE TYPE network_enum AS ENUM ('ethereum', 'polygon', 'arbitrum', 'solana');

-- API Keys table
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key_id VARCHAR(255) UNIQUE NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    environment VARCHAR(50) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    name VARCHAR(255),
    description TEXT,
    permissions JSONB NOT NULL DEFAULT '{}',
    last_used_at TIMESTAMPTZ,
    request_count INTEGER NOT NULL DEFAULT 0,
    user_email VARCHAR(255),
    organization VARCHAR(255),
    user_metadata JSONB NOT NULL DEFAULT '{}',
    rate_limit_per_hour INTEGER NOT NULL DEFAULT 1000,
    monthly_quota INTEGER,
    current_month_usage INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Agents table
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id VARCHAR(255) UNIQUE NOT NULL,
    api_key_id UUID NOT NULL REFERENCES api_keys(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    capabilities JSONB NOT NULL DEFAULT '{}',
    wallet_address VARCHAR(255) NOT NULL,
    supported_currencies JSONB NOT NULL DEFAULT '{}',
    supported_networks JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT true,
    last_seen_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Services table
CREATE TABLE services (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_id VARCHAR(255) UNIQUE NOT NULL,
    agent_id UUID NOT NULL REFERENCES agents(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    price FLOAT NOT NULL,
    currency currency_enum NOT NULL,
    network network_enum NOT NULL,
    x402_endpoint VARCHAR(500) NOT NULL,
    payment_method payment_method_enum NOT NULL DEFAULT 'crypto',
    is_active BOOLEAN NOT NULL DEFAULT true,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Wallets table
CREATE TABLE wallets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wallet_id VARCHAR(255) UNIQUE NOT NULL,
    agent_id UUID NOT NULL REFERENCES agents(id),
    address VARCHAR(255) NOT NULL,
    network network_enum NOT NULL,
    wallet_type VARCHAR(50) NOT NULL DEFAULT 'hot',
    is_multisig BOOLEAN NOT NULL DEFAULT false,
    required_signatures INTEGER DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT true,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Wallet Balances table
CREATE TABLE wallet_balances (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wallet_id UUID NOT NULL REFERENCES wallets(id),
    currency currency_enum NOT NULL,
    balance FLOAT NOT NULL DEFAULT 0.0,
    reserved FLOAT NOT NULL DEFAULT 0.0,
    available FLOAT NOT NULL DEFAULT 0.0,
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_sync_block INTEGER DEFAULT 0,
    UNIQUE(wallet_id, currency)
);

-- Payments table
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    payment_id VARCHAR(255) UNIQUE NOT NULL,
    from_agent_id UUID NOT NULL REFERENCES agents(id),
    to_agent_id UUID NOT NULL REFERENCES agents(id),
    amount FLOAT NOT NULL,
    currency currency_enum NOT NULL,
    network network_enum NOT NULL,
    method payment_method_enum NOT NULL DEFAULT 'crypto',
    disco_fee FLOAT NOT NULL DEFAULT 0.0,
    disco_fee_percentage_amount FLOAT NOT NULL DEFAULT 0.0,
    disco_fee_fixed_amount FLOAT NOT NULL DEFAULT 0.0,
    disco_fee_percentage FLOAT NOT NULL DEFAULT 0.029,
    disco_fee_fixed FLOAT NOT NULL DEFAULT 0.30,
    net_amount FLOAT NOT NULL,
    status payment_status_enum NOT NULL DEFAULT 'pending',
    description TEXT,
    reference VARCHAR(255),
    transaction_hash VARCHAR(255),
    block_number INTEGER,
    gas_used INTEGER,
    gas_price FLOAT,
    x402_payment_id VARCHAR(255),
    x402_signature TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'
);

-- Transactions table
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transaction_id VARCHAR(255) UNIQUE NOT NULL,
    hash VARCHAR(255) UNIQUE NOT NULL,
    network network_enum NOT NULL,
    block_number INTEGER,
    block_hash VARCHAR(255),
    transaction_index INTEGER,
    from_address VARCHAR(255) NOT NULL,
    to_address VARCHAR(255) NOT NULL,
    value FLOAT NOT NULL,
    gas_limit INTEGER NOT NULL,
    gas_used INTEGER,
    gas_price FLOAT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    confirmations INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    confirmed_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'
);

-- Webhook Events table
CREATE TABLE webhook_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id VARCHAR(255) UNIQUE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(255) NOT NULL,
    webhook_url VARCHAR(500) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    response_status INTEGER,
    response_body TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    scheduled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMPTZ
);

-- USAGE TRACKING TABLES (NEW)

-- Audit Logs table
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(100) NOT NULL,
    api_key_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),
    resource_id VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,
    sdk_version VARCHAR(50),
    environment VARCHAR(50),
    details JSONB NOT NULL DEFAULT '{}',
    success BOOLEAN NOT NULL DEFAULT true,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Usage Statistics table
CREATE TABLE usage_statistics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    api_key_id VARCHAR(255) NOT NULL,
    date TIMESTAMPTZ NOT NULL,
    period_type VARCHAR(20) NOT NULL,
    total_requests INTEGER NOT NULL DEFAULT 0,
    unique_agents INTEGER NOT NULL DEFAULT 0,
    total_payments INTEGER NOT NULL DEFAULT 0,
    payment_volume FLOAT NOT NULL DEFAULT 0.0,
    fees_collected FLOAT NOT NULL DEFAULT 0.0,
    services_created INTEGER NOT NULL DEFAULT 0,
    services_consumed INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    error_rate FLOAT NOT NULL DEFAULT 0.0,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_api_keys_key_id ON api_keys(key_id);
CREATE INDEX idx_agents_agent_id ON agents(agent_id);
CREATE INDEX idx_agents_wallet_address ON agents(wallet_address);
CREATE INDEX idx_services_service_id ON services(service_id);
CREATE INDEX idx_wallets_wallet_id ON wallets(wallet_id);
CREATE INDEX idx_wallets_address ON wallets(address);
CREATE INDEX idx_payments_payment_id ON payments(payment_id);
CREATE INDEX idx_payments_transaction_hash ON payments(transaction_hash);
CREATE INDEX idx_payment_status ON payments(status);
CREATE INDEX idx_payment_created_at ON payments(created_at);
CREATE INDEX idx_payment_agents ON payments(from_agent_id, to_agent_id);
CREATE INDEX idx_transactions_transaction_id ON transactions(transaction_id);
CREATE INDEX idx_transactions_hash ON transactions(hash);
CREATE INDEX idx_transaction_network ON transactions(network);
CREATE INDEX idx_transaction_addresses ON transactions(from_address, to_address);
CREATE INDEX idx_transaction_status ON transactions(status);
CREATE INDEX idx_webhook_events_event_id ON webhook_events(event_id);
CREATE INDEX idx_webhook_events_event_type ON webhook_events(event_type);
CREATE INDEX idx_webhook_events_resource_id ON webhook_events(resource_id);
CREATE INDEX idx_webhook_status ON webhook_events(status);
CREATE INDEX idx_webhook_scheduled ON webhook_events(scheduled_at);
CREATE INDEX idx_webhook_resource ON webhook_events(resource_type, resource_id);

-- Usage tracking indexes
CREATE INDEX idx_audit_event_type ON audit_logs(event_type);
CREATE INDEX idx_audit_api_key ON audit_logs(api_key_id);
CREATE INDEX idx_audit_timestamp ON audit_logs(created_at);
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_usage_api_key_date ON usage_statistics(api_key_id, date);
CREATE INDEX idx_usage_period ON usage_statistics(period_type, date);
```

</details>

## ⚡ Quick Railway Setup Commands

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login and link project
railway login
railway link

# 3. Add PostgreSQL service
railway add postgresql

# 4. Set environment variables
railway variables set DISCO_ENVIRONMENT=production
railway variables set ENABLE_USAGE_TRACKING=true
railway variables set ANALYTICS_RETENTION_DAYS=90

# 5. Deploy
railway deploy
```

## 🔧 Post-Deployment Configuration

### 1. Create First Admin API Key
```python
# Run this in Railway's console or via a migration script
import hashlib
import secrets
from datetime import datetime

# Generate admin API key
admin_key = "dk_live_admin_" + secrets.token_urlsafe(32)
key_hash = hashlib.sha256(admin_key.encode()).hexdigest()
key_id = f"dk_live_admin_{secrets.token_hex(8)}"

# Insert into database
INSERT INTO api_keys (
    key_id, key_hash, environment, user_email, organization, 
    name, description, rate_limit_per_hour, monthly_quota
) VALUES (
    '{key_id}', '{key_hash}', 'live', 'admin@yourdomain.com', 'Disco Admin',
    'Admin API Key', 'Administrative access for platform analytics',
    100000, NULL
);

print(f"Admin API Key: {admin_key}")
```

### 2. Test Analytics Endpoints
```bash
# Test user registration
curl -X POST https://your-app.railway.app/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "organization": "Test Org",
    "name": "Test User",
    "environment": "sandbox"
  }'

# Test analytics (use returned API key)
curl -X GET https://your-app.railway.app/analytics/usage \
  -H "Authorization: Bearer dk_test_xxx"
```

### 3. Access Analytics Dashboard
Visit: `https://your-app.railway.app/analytics/dashboard`

## 📊 Monitoring & Maintenance

### Database Size Monitoring
```sql
-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Cleanup Old Data
```sql
-- Clean up audit logs older than 90 days
DELETE FROM audit_logs 
WHERE created_at < NOW() - INTERVAL '90 days';

-- Clean up old usage statistics
DELETE FROM usage_statistics 
WHERE created_at < NOW() - INTERVAL '1 year';
```

## 🚨 Troubleshooting

### Common Issues

1. **Migration Fails**
   ```bash
   # Reset and retry
   railway run alembic downgrade base
   railway run alembic upgrade head
   ```

2. **Missing Dependencies**
   ```bash
   # Add to requirements.txt
   echo "alembic==1.12.1" >> requirements.txt
   echo "asyncpg==0.28.0" >> requirements.txt
   ```

3. **Database Connection Issues**
   ```bash
   # Check DATABASE_URL format
   railway variables get DATABASE_URL
   ```

4. **Performance Issues**
   ```sql
   -- Add missing indexes
   CREATE INDEX CONCURRENTLY idx_audit_logs_created_at 
   ON audit_logs(created_at DESC);
   ```

## 📈 Scaling Considerations

### For High Traffic (>1M requests/day)
1. **Enable Connection Pooling**
2. **Add Redis for Caching**
3. **Partition Large Tables**
4. **Use Background Jobs for Analytics**

### Database Partitioning Example
```sql
-- Partition audit_logs by month
CREATE TABLE audit_logs_2024_01 PARTITION OF audit_logs
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

This deployment will give you a fully functional usage tracking system on Railway with comprehensive analytics capabilities. 