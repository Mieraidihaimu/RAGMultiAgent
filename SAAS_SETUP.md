# SaaS Landing Page & Payment Integration Setup

This guide will help you set up the SaaS landing page with Stripe payment integration for your AI Thought Processor.

## 📋 What's New

We've added a complete SaaS landing page with:

- **Modern Landing Page** ([landing.html](frontend/landing.html))
  - Hero section with CTA
  - Features showcase
  - How it works section
  - Pricing tiers (Free, Pro, Enterprise)
  - Testimonials
  - Footer with links

- **Checkout Page** ([checkout.html](frontend/checkout.html))
  - Stripe payment integration
  - Order summary
  - Secure payment form
  - Free plan support

- **Login/Signup Page** ([login.html](frontend/login.html))
  - Email/password authentication
  - Social login placeholders (Google, GitHub)
  - Account creation flow

- **Payment API Routes** ([api/payment_routes.py](api/payment_routes.py))
  - Create subscriptions
  - Create free accounts
  - Cancel subscriptions
  - Webhook handling
  - Subscription management

## 🚀 Quick Start

### 1. Install Stripe Dependency

```bash
pip install stripe==8.2.0
```

Or rebuild your Docker containers:

```bash
docker compose down
docker compose up -d --build
```

### 2. Get Your Stripe API Keys

1. Go to [Stripe Dashboard](https://dashboard.stripe.com/)
2. Create an account or log in
3. Navigate to **Developers** → **API keys**
4. Copy your **Publishable key** and **Secret key**

For testing, use **Test mode** keys (they start with `pk_test_` and `sk_test_`)

### 3. Configure Environment Variables

Add to your `.env` file:

```bash
# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here  # Optional, for webhooks
```

### 4. Update Frontend Stripe Key

Edit [frontend/checkout.html](frontend/checkout.html) and replace:

```javascript
const STRIPE_PUBLIC_KEY = 'pk_test_YOUR_STRIPE_PUBLISHABLE_KEY';
```

With your actual publishable key:

```javascript
const STRIPE_PUBLIC_KEY = 'pk_test_51abc123...';
```

### 5. Run Database Migration

Apply the subscription tables migration:

```bash
docker compose exec db psql -U thoughtprocessor -d thoughtprocessor -f /docker-entrypoint-initdb.d/migrations/002_add_subscriptions.sql
```

Or if running locally:

```bash
psql -U thoughtprocessor -d thoughtprocessor -f database/migrations/002_add_subscriptions.sql
```

### 6. Access the Landing Page

Open your browser and navigate to:

```
http://localhost:3000/landing.html
```

## 🎨 Page Structure

### Landing Page Flow

```
landing.html
    ↓ (Click "Get Started")
login.html
    ↓ (Create account)
checkout.html?plan=pro
    ↓ (Complete payment)
index.html (Dashboard)
```

### File Overview

```
frontend/
├── landing.html      # Main SaaS landing page
├── checkout.html     # Payment checkout
├── login.html        # Authentication
├── index.html        # Dashboard (existing)
└── detail.html       # Thought details (existing)

api/
├── main.py           # Main API (updated with payment routes)
├── payment_routes.py # Stripe integration endpoints
└── ...

database/
└── migrations/
    └── 002_add_subscriptions.sql  # Subscription tables
```

## 💳 Stripe Test Cards

For testing payments, use these test cards:

| Card Number         | Description           |
|--------------------|-----------------------|
| 4242 4242 4242 4242 | Success              |
| 4000 0025 0000 3155 | 3D Secure required   |
| 4000 0000 0000 9995 | Declined             |

**Expiry:** Any future date
**CVC:** Any 3 digits
**ZIP:** Any valid ZIP code

## 📊 Pricing Plans

### Free Plan ($0/month)
- 10 thoughts per month
- Basic analysis
- Email support
- Dashboard access

### Pro Plan ($19/month)
- Unlimited thoughts
- Advanced AI analysis
- Priority support
- Weekly synthesis reports
- Export to PDF
- API access

### Enterprise Plan (Custom)
- Everything in Pro
- Team collaboration
- Custom AI models
- Dedicated support
- SLA guarantee
- On-premise deployment

## 🔧 API Endpoints

### Payment Routes

```bash
# Create a subscription
POST /api/create-subscription
{
  "payment_method_id": "pm_xxx",
  "email": "user@example.com",
  "name": "John Doe",
  "plan": "pro"
}

# Create free account
POST /api/create-free-account
{
  "email": "user@example.com",
  "name": "John Doe"
}

# Cancel subscription
POST /api/cancel-subscription
{
  "subscription_id": "sub_xxx"
}

# Get subscription details
GET /api/subscription/{user_id}

# Stripe webhook (for production)
POST /api/webhook
```

## 🔐 Security Considerations

### For Production

1. **Update CORS settings** in [api/main.py](api/main.py):
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://yourdomain.com"],  # Specific domain
       allow_credentials=True,
       allow_methods=["GET", "POST"],
       allow_headers=["*"],
   )
   ```

2. **Use environment variables** for all sensitive data
3. **Enable HTTPS** for your domain
4. **Set up Stripe webhooks** for production:
   - Go to Stripe Dashboard → Webhooks
   - Add endpoint: `https://yourdomain.com/api/webhook`
   - Select events: `invoice.payment_succeeded`, `invoice.payment_failed`, `customer.subscription.deleted`
   - Copy webhook secret to `STRIPE_WEBHOOK_SECRET`

5. **Implement proper authentication**:
   - Add JWT token authentication
   - Secure password hashing (bcrypt)
   - Rate limiting
   - CSRF protection

## 🧪 Testing the Flow

### Test Free Plan

1. Open `http://localhost:3000/landing.html`
2. Click "Get Started" on Free plan
3. Create an account (no payment required)
4. Redirected to dashboard

### Test Pro Plan

1. Open `http://localhost:3000/landing.html`
2. Click "Start Free Trial" on Pro plan
3. Create account or login
4. Enter test card: `4242 4242 4242 4242`
5. Complete checkout
6. Redirected to dashboard

## 🎯 Next Steps

### Recommended Improvements

1. **Authentication System**
   - Implement JWT-based auth
   - Add password reset functionality
   - Enable OAuth (Google, GitHub)

2. **User Dashboard**
   - Show subscription details
   - Add upgrade/downgrade options
   - Display usage statistics

3. **Email Integration**
   - Welcome emails
   - Payment receipts
   - Weekly reports

4. **Analytics**
   - Track conversions
   - Monitor churn
   - Analyze user behavior

5. **Additional Features**
   - Team collaboration (Enterprise)
   - API key management
   - Custom AI model selection

## 📝 Environment Variables Reference

Add these to your `.env` file:

```bash
# Existing variables...
AI_PROVIDER=google
GOOGLE_API_KEY=your_key_here

# Database
DATABASE_URL=postgresql://thoughtprocessor:password@db:5432/thoughtprocessor

# API Configuration
API_PORT=8000
API_HOST=0.0.0.0
DEBUG=true

# Stripe (NEW)
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here

# Email (Optional - for future use)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

## 🐛 Troubleshooting

### Payment routes not loading

**Error:** `Payment routes not available`

**Solution:** Install stripe:
```bash
pip install stripe==8.2.0
# or
docker compose up -d --build
```

### Stripe key errors

**Error:** `Invalid API key provided`

**Solution:**
1. Check your `.env` file has the correct keys
2. Make sure you're using test mode keys for development
3. Verify keys don't have extra spaces or quotes

### Database migration fails

**Error:** `relation "users" does not exist`

**Solution:** Run the base schema first:
```bash
docker compose exec db psql -U thoughtprocessor -d thoughtprocessor -f /docker-entrypoint-initdb.d/schema.sql
```

### CORS errors in browser

**Error:** `Access-Control-Allow-Origin`

**Solution:** Verify CORS is enabled in [api/main.py](api/main.py) and restart the API:
```bash
docker compose restart api
```

## 📚 Additional Resources

- [Stripe Documentation](https://stripe.com/docs)
- [Stripe Testing Guide](https://stripe.com/docs/testing)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Stripe Webhooks Guide](https://stripe.com/docs/webhooks)

## 💡 Tips

1. **Start with Free Plan**: Test the entire flow without payments first
2. **Use Test Mode**: Always use Stripe test mode for development
3. **Monitor Logs**: Check Docker logs for any errors:
   ```bash
   docker compose logs -f api
   ```
4. **Test Webhooks Locally**: Use Stripe CLI for local webhook testing:
   ```bash
   stripe listen --forward-to localhost:8000/api/webhook
   ```

## 🎉 You're All Set!

Your AI Thought Processor now has a complete SaaS landing page with payment integration. Users can:

- Browse features and pricing
- Sign up for free or paid plans
- Make secure payments via Stripe
- Access their personalized dashboard
- Manage their subscriptions

Happy coding! 🚀
