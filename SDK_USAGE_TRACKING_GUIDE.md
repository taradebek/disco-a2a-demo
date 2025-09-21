# Disco SDK Usage Tracking & User Identification Guide

## Overview

This guide explains how to comprehensively track SDK usage and identify users in your Disco platform. The implementation provides detailed analytics, user identification, and usage monitoring capabilities.

## 🎯 What You Can Track

### User Identification
- **Email addresses** - Primary user identifier
- **Organization names** - Company/team identification
- **User metadata** - Custom information (use case, expected volume, etc.)
- **IP addresses** - Geographic and security tracking
- **User-Agent strings** - SDK version and client information

### Usage Analytics
- **API request counts** - Total and per-endpoint usage
- **Payment metrics** - Volume, count, fees collected
- **Agent activity** - Agent creation and service usage
- **Error rates** - Success/failure tracking
- **Response times** - Performance monitoring
- **Geographic distribution** - IP-based location tracking

### Platform Metrics
- **Total users** - Overall platform adoption
- **Active users** - 30-day activity tracking
- **SDK version distribution** - Version adoption rates
- **Top organizations** - High-usage customers
- **Growth trends** - Time-series analytics

## 🏗️ Implementation Components

### 1. Database Models

#### Enhanced API Key Model
```python
class APIKey(Base):
    # Basic fields
    key_id: str
    key_hash: str
    environment: str
    
    # User identification
    user_email: Optional[str]
    organization: Optional[str]
    user_metadata: Dict[str, Any]
    
    # Usage tracking
    request_count: int
    last_used_at: Optional[datetime]
    current_month_usage: int
    
    # Limits and quotas
    rate_limit_per_hour: int
    monthly_quota: Optional[int]
```

#### Audit Log Model
```python
class AuditLog(Base):
    event_type: str
    api_key_id: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    sdk_version: Optional[str]
    success: bool
    details: Dict[str, Any]
    created_at: datetime
```

#### Usage Statistics Model
```python
class UsageStatistics(Base):
    api_key_id: str
    date: datetime
    period_type: str  # daily, weekly, monthly
    total_requests: int
    payment_volume: float
    error_count: int
```

### 2. SDK Enhancements

#### User Information Collection
```python
disco = Disco(
    api_key="dk_test_xxx",
    user_email="developer@company.com",
    organization="TechCorp Inc",
    user_metadata={
        "use_case": "AI agent payments",
        "expected_volume": "1000 transactions/month"
    }
)
```

#### Automatic Header Injection
- `User-Agent`: `disco-sdk-python/1.0.0`
- `X-User-Email`: User's email address
- `X-Organization`: Organization name
- `X-Disco-Environment`: sandbox/live

### 3. Analytics Service

#### Usage Tracking
```python
await analytics_service.track_api_usage(
    api_key_id=api_key,
    endpoint="/payments",
    method="POST",
    ip_address="192.168.1.1",
    user_agent="disco-sdk-python/1.0.0",
    success=True,
    response_time_ms=245.5
)
```

#### Analytics Retrieval
```python
analytics = await analytics_service.get_usage_analytics(
    api_key_id=api_key,
    start_date=datetime.now() - timedelta(days=30),
    granularity="daily"
)
```

### 4. API Endpoints

#### User Registration
```http
POST /users/register
{
    "email": "developer@company.com",
    "organization": "TechCorp Inc",
    "name": "John Developer",
    "use_case": "AI agent payments",
    "environment": "sandbox"
}
```

#### Usage Analytics
```http
GET /analytics/usage?start_date=2024-01-01&granularity=daily
Authorization: Bearer dk_test_xxx
```

#### User Information
```http
GET /analytics/user-info
Authorization: Bearer dk_test_xxx
```

#### Platform Analytics (Admin)
```http
GET /analytics/platform
Authorization: Bearer dk_live_admin_xxx
```

## 📊 Analytics Dashboard

### Key Metrics Displayed
- Total registered users
- Active users (30-day window)
- Total payment count and volume
- SDK version distribution
- Top organizations by usage
- Geographic distribution
- Error rates and response times

### Real-time Features
- Auto-refreshing every 5 minutes
- Interactive charts using Chart.js
- Responsive design for mobile/desktop
- Error handling and fallback data

## 🔧 Usage Examples

### 1. Basic User Registration
```python
import requests

# Register new user
response = requests.post('/users/register', json={
    "email": "newuser@startup.com",
    "organization": "AI Startup",
    "name": "Jane Smith",
    "use_case": "Multi-agent marketplace",
    "expected_volume": "500 transactions/month",
    "environment": "sandbox"
})

api_key = response.json()["api_key"]
```

### 2. SDK with User Tracking
```python
from disco_sdk import Disco

# Initialize with user information
disco = Disco(
    api_key="dk_test_abc123",
    user_email="developer@company.com",
    organization="TechCorp Inc",
    user_metadata={
        "team": "AI Research",
        "project": "Agent Collaboration Platform"
    }
)

# All API calls are automatically tracked
payment = await disco.pay(
    to_agent="supplier_agent",
    amount=10.0,
    currency="USDC"
)
```

### 3. Retrieving Analytics
```python
import requests

# Get usage analytics
headers = {"Authorization": "Bearer dk_test_abc123"}
analytics = requests.get('/analytics/usage', headers=headers).json()

print(f"Total requests: {analytics['overview']['total_requests']}")
print(f"Payment volume: ${analytics['payments']['volume']}")
print(f"Error rate: {analytics['overview']['error_rate']}%")
```

## 🔍 Monitoring & Insights

### User Behavior Tracking
- **API endpoint preferences** - Which endpoints are used most
- **Usage patterns** - Peak usage times and frequency
- **Feature adoption** - Which SDK features are popular
- **Error patterns** - Common failure points

### Business Intelligence
- **Customer segmentation** - By organization size and usage
- **Revenue attribution** - Fees collected per user/organization
- **Churn prediction** - Users with declining activity
- **Growth opportunities** - High-value user identification

### Security Monitoring
- **Unusual activity** - Abnormal request patterns
- **Geographic anomalies** - Requests from unexpected locations
- **Rate limit violations** - Users exceeding quotas
- **Failed authentication** - Invalid API key usage

## 🚀 Implementation Steps

### Phase 1: Database Setup
1. Run database migrations for new models
2. Update existing API keys with user information
3. Set up audit logging infrastructure

### Phase 2: SDK Enhancement
1. Update SDK to collect user information
2. Add automatic header injection
3. Implement client-side usage tracking

### Phase 3: Analytics Backend
1. Deploy analytics service
2. Set up automated data aggregation
3. Implement real-time tracking

### Phase 4: API & Dashboard
1. Deploy analytics API endpoints
2. Create usage dashboard
3. Set up monitoring alerts

### Phase 5: User Onboarding
1. Update registration flow
2. Migrate existing users
3. Provide analytics access to customers

## 📈 Advanced Features

### Custom Events
```python
# Track custom business events
await analytics_service.track_api_usage(
    api_key_id=api_key,
    endpoint="custom_event",
    method="EVENT",
    success=True,
    details={
        "event_name": "agent_collaboration_started",
        "participants": ["agent1", "agent2"],
        "collaboration_type": "procurement"
    }
)
```

### Webhook Integration
```python
# Send usage alerts via webhooks
if monthly_usage > quota * 0.8:
    await webhook_service.send_webhook(
        url=user_webhook_url,
        event_type="usage_warning",
        data={
            "usage_percentage": 85,
            "current_usage": monthly_usage,
            "quota": quota
        }
    )
```

### Data Export
```python
# Export usage data
export_data = requests.get(
    '/analytics/export?format=json&start_date=2024-01-01',
    headers=headers
).json()
```

## 🔐 Privacy & Security

### Data Protection
- Hash API keys before storage
- Encrypt sensitive user metadata
- Implement data retention policies
- Provide user data deletion

### Access Control
- Role-based analytics access
- API key scoping for analytics
- Admin-only platform metrics
- User-specific data isolation

### Compliance
- GDPR-compliant data handling
- User consent for tracking
- Data anonymization options
- Audit trail maintenance

## 📊 Sample Analytics Output

```json
{
  "period": {
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-01-31T23:59:59Z",
    "granularity": "daily"
  },
  "overview": {
    "total_requests": 15420,
    "error_count": 23,
    "error_rate": 0.15,
    "unique_agents": 12,
    "services_created": 8
  },
  "payments": {
    "count": 1250,
    "volume": 125000.50,
    "fees_collected": 3625.01
  },
  "time_series": [
    {
      "period": "2024-01-01T00:00:00Z",
      "requests": 450,
      "errors": 2,
      "error_rate": 0.44
    }
  ],
  "top_endpoints": [
    {
      "endpoint": "/payments",
      "count": 8500,
      "avg_response_time_ms": 245.5
    }
  ]
}
```

This comprehensive tracking system gives you complete visibility into SDK usage, user behavior, and platform adoption while maintaining privacy and security standards. 