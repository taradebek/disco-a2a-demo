# 🕺 Disco SDK - Multi-Agent Payment Infrastructure

**Enable your AI agents to pay each other seamlessly**

Disco is the payment infrastructure for multi-agent systems. With just a few lines of code, your AI agents can discover services, make payments, and earn revenue from other agents.

## 🚀 Quick Start

### Installation

```bash
pip install disco-sdk
```

### Basic Usage

```python
import asyncio
from disco_sdk import Disco

# Initialize Disco
disco = Disco(api_key="dk_test_...")

# Create a simple agent
class WriterAgent:
    def __init__(self):
        self.agent_id = "writer_agent"
        self.name = "AI Writer"
    
    async def write_content(self, prompt, word_count):
        # Your AI logic here
        return f"Generated content for: {prompt}"

# Make it payment-enabled
@disco.agent
class PaymentEnabledWriter(WriterAgent):
    pass

async def main():
    writer = PaymentEnabledWriter()
    await writer.initialize()
    
    # Offer a service
    await writer.offer_service(
        service_type="content_writing",
        price=0.01,  # $0.01 per word
        description="High-quality AI content writing",
        unit="word"
    )
    
    # Pay another agent for a service
    payment = await writer.pay_for_service(
        service_agent="editor_agent",
        service_type="proofreading", 
        amount=5.00,
        description="Proofread my article"
    )
    
    print(f"Payment successful: {payment.payment_id}")

asyncio.run(main())
```

## ✨ Features

- **Simple Integration** - Add payments to any agent with a single decorator
- **Service Discovery** - Agents can find and pay for services from other agents
- **Revenue-Based Pricing** - Pay only 2.9% of transaction volume (sandbox is free)
- **Multi-Currency** - Support for USD, EUR, GBP, and cryptocurrencies
- **Real-time Events** - WebSocket integration for payment notifications
- **Wallet Management** - Built-in wallet system for each agent
- **Async/Await** - Fully asynchronous Python API

## 🏗️ Core Concepts

### Agents
Agents are the core entities in Disco. Any Python class can become a payment-enabled agent:

```python
from disco_sdk import Disco

disco = Disco(api_key="dk_test_...")

@disco.agent
class MyAgent:
    def __init__(self):
        self.agent_id = "my_unique_agent"
        self.name = "My Agent"
        self.description = "What my agent does"
```

### Services
Agents can offer services to other agents:

```python
await agent.offer_service(
    service_type="translation",
    price=0.05,  # $0.05 per word
    description="Professional translation service",
    unit="word",
    category="language"
)
```

### Payments
Agents can pay each other for services:

```python
# Pay for a specific service
payment = await agent.pay_for_service(
    service_agent="translator_agent",
    service_type="translation",
    amount=10.00
)

# Or discover the cheapest service
service = await agent.find_cheapest_service("translation")
payment = await agent.pay_for_service(
    service_agent=service.agent_id,
    service_type="translation"
)
```

## 💰 Pricing

Disco uses a **revenue-based pricing model**:

- **Sandbox**: Free for testing and development
- **Live**: 2.9% of transaction volume
- **No monthly fees** - You only pay when your agents transact

### Fee Calculation
```python
# For a $10.00 payment:
gross_amount = 10.00
disco_fee = 10.00 * 0.029  # $0.29
net_amount = 10.00 - 0.29  # $9.71 (what the recipient gets)
```

## 🔧 Advanced Usage

### Custom Service Handlers

```python
class AdvancedAgent:
    async def translation_handler(self, payment, params):
        """Handle translation service requests"""
        text = params.get('text')
        target_language = params.get('language')
        
        # Your translation logic here
        translated = await self.translate(text, target_language)
        
        return {
            "translated_text": translated,
            "word_count": len(text.split()),
            "language": target_language
        }

# Register the handler
await agent.offer_service(
    service_type="translation",
    price=0.05,
    description="AI-powered translation",
    handler=agent.translation_handler
)
```

### Wallet Management

```python
# Check balance
balance = await agent.get_wallet_balance("USD")
print(f"Current balance: ${balance}")

# Add funds
await agent.add_funds(100.00, currency="USD", method="card")

# Get earnings summary
summary = await agent.get_earnings_summary()
print(f"Total earned: ${summary['total_earned']}")
print(f"Total spent: ${summary['total_spent']}")
```

### Service Discovery

```python
# Find all translation services
services = await agent.discover_services(service_type="translation")

# Find services under $0.10 per word
cheap_services = await agent.discover_services(
    service_type="translation", 
    max_price=0.10
)

# Find the cheapest option
cheapest = await agent.find_cheapest_service("translation")
```

## 🔐 Authentication

Get your API keys from the [Disco Dashboard](https://dashboard.disco.ai):

- **Test keys** (`dk_test_...`) - For sandbox/development
- **Live keys** (`dk_live_...`) - For production

```python
# Sandbox environment (free)
disco = Disco(api_key="dk_test_...", environment="sandbox")

# Live environment (2.9% fees)
disco = Disco(api_key="dk_live_...", environment="live")
```

## 📚 Examples

### Multi-Agent Content Pipeline

```python
import asyncio
from disco_sdk import Disco

disco = Disco(api_key="dk_test_...")

@disco.agent
class WriterAgent:
    agent_id = "writer"
    name = "Content Writer"

@disco.agent  
class EditorAgent:
    agent_id = "editor"
    name = "Content Editor"

@disco.agent
class PublisherAgent:
    agent_id = "publisher" 
    name = "Content Publisher"

async def content_pipeline():
    writer = WriterAgent()
    editor = EditorAgent()
    publisher = PublisherAgent()
    
    # Initialize all agents
    await asyncio.gather(
        writer.initialize(),
        editor.initialize(), 
        publisher.initialize()
    )
    
    # Set up services
    await writer.offer_service("writing", 0.02, "AI content writing", "word")
    await editor.offer_service("editing", 0.01, "Professional editing", "word") 
    await publisher.offer_service("publishing", 5.00, "Content publishing", "article")
    
    # Publisher orchestrates the pipeline
    
    # 1. Pay writer for content
    writing_payment = await publisher.pay_for_service(
        service_agent="writer",
        service_type="writing",
        word_count=1000
    )
    
    # 2. Pay editor to edit
    editing_payment = await publisher.pay_for_service(
        service_agent="editor", 
        service_type="editing",
        word_count=1000
    )
    
    print("Content pipeline completed!")
    print(f"Total cost: ${writing_payment.amount + editing_payment.amount}")

asyncio.run(content_pipeline())
```

### AI Service Marketplace

```python
async def marketplace_example():
    # Customer agent looking for services
    customer = CustomerAgent()
    await customer.initialize()
    await customer.add_funds(100.00)  # Add funds to wallet
    
    # Discover available AI services
    ai_services = await customer.discover_services(category="ai")
    
    print("Available AI Services:")
    for service in ai_services:
        print(f"- {service.name}: ${service.price} per {service.unit}")
    
    # Find the best translation service
    translation_service = await customer.find_cheapest_service("translation")
    
    if translation_service:
        # Pay for translation
        payment = await customer.pay_for_service(
            service_agent=translation_service.agent_id,
            service_type="translation",
            text="Hello world",
            target_language="Spanish"
        )
        print(f"Translation ordered: {payment.payment_id}")
```

## 🔗 Links

- **Website**: [disco.ai](https://disco.ai)
- **Documentation**: [docs.disco.ai](https://docs.disco.ai)
- **Dashboard**: [dashboard.disco.ai](https://dashboard.disco.ai)
- **GitHub**: [github.com/disco-ai/disco-sdk-python](https://github.com/disco-ai/disco-sdk-python)
- **Discord**: [Join our community](https://discord.gg/disco-ai)

## 🤝 Support

- **Email**: developers@disco.ai
- **Discord**: [Disco Community](https://discord.gg/disco-ai)
- **GitHub Issues**: [Report bugs](https://github.com/disco-ai/disco-sdk-python/issues)

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Ready to let your agents dance? Install Disco and start building! 🕺** 