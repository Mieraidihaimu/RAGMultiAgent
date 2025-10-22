"""
Payment and subscription endpoints for Stripe integration
"""
import os
import stripe
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from loguru import logger

from database import get_db
from common.database.base import DatabaseAdapter

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

router = APIRouter(prefix="/api", tags=["Payments"])

# Pydantic models
class CreateSubscriptionRequest(BaseModel):
    payment_method_id: str
    email: EmailStr
    name: str
    plan: str  # 'pro' or 'enterprise'

class CreateFreeAccountRequest(BaseModel):
    email: EmailStr
    name: str

class SubscriptionResponse(BaseModel):
    status: str
    subscription_id: Optional[str] = None
    client_secret: Optional[str] = None
    error: Optional[str] = None

class FreeAccountResponse(BaseModel):
    success: bool
    user_id: Optional[str] = None
    error: Optional[str] = None

class CancelSubscriptionRequest(BaseModel):
    subscription_id: str

# Plan pricing (in cents)
PLAN_PRICES = {
    'pro': 1900,  # $19.00
    'enterprise': 9900  # $99.00
}

@router.post("/create-subscription", response_model=SubscriptionResponse)
async def create_subscription(
    request: CreateSubscriptionRequest,
    db: DatabaseAdapter = Depends(get_db)
):
    """
    Create a Stripe subscription for a paid plan
    """
    try:
        if not stripe.api_key or stripe.api_key == "":
            logger.warning("Stripe API key not configured")
            return SubscriptionResponse(
                status="error",
                error="Payment system not configured. Please contact support."
            )

        # Validate plan
        if request.plan not in PLAN_PRICES:
            raise HTTPException(status_code=400, detail="Invalid plan selected")

        # Create or retrieve customer
        customer = stripe.Customer.create(
            email=request.email,
            name=request.name,
            payment_method=request.payment_method_id,
            invoice_settings={
                'default_payment_method': request.payment_method_id,
            },
        )

        # Create subscription
        subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[
                {
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f'AI Thought Processor - {request.plan.title()} Plan',
                        },
                        'unit_amount': PLAN_PRICES[request.plan],
                        'recurring': {
                            'interval': 'month',
                        },
                    },
                },
            ],
            payment_behavior='default_incomplete',
            payment_settings={'save_default_payment_method': 'on_subscription'},
            expand=['latest_invoice.payment_intent'],
        )

        # Create user account in database
        user_id = str(uuid4())
        await db.execute(
            """
            INSERT INTO users (id, email, created_at, subscription_plan, subscription_id, stripe_customer_id)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (email) DO UPDATE
            SET subscription_plan = $4, subscription_id = $5, stripe_customer_id = $6
            RETURNING id
            """,
            user_id, request.email, datetime.utcnow(), request.plan, subscription.id, customer.id
        )

        logger.info(f"Subscription created for {request.email}: {subscription.id}")

        return SubscriptionResponse(
            status=subscription.status,
            subscription_id=subscription.id,
            client_secret=subscription.latest_invoice.payment_intent.client_secret
        )

    except stripe.error.CardError as e:
        logger.error(f"Card error: {e.user_message}")
        return SubscriptionResponse(
            status="error",
            error=e.user_message
        )
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)}")
        return SubscriptionResponse(
            status="error",
            error="Payment processing failed. Please try again."
        )
    except Exception as e:
        logger.error(f"Unexpected error creating subscription: {str(e)}")
        return SubscriptionResponse(
            status="error",
            error="An unexpected error occurred. Please try again."
        )


@router.post("/create-free-account", response_model=FreeAccountResponse)
async def create_free_account(
    request: CreateFreeAccountRequest,
    db: DatabaseAdapter = Depends(get_db)
):
    """
    Create a free account without payment
    """
    try:
        user_id = str(uuid4())

        # Create user in database
        await db.execute(
            """
            INSERT INTO users (id, email, created_at, subscription_plan)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (email) DO UPDATE
            SET subscription_plan = $4
            RETURNING id
            """,
            user_id, request.email, datetime.utcnow(), 'free'
        )

        logger.info(f"Free account created for {request.email}")

        return FreeAccountResponse(
            success=True,
            user_id=user_id
        )

    except Exception as e:
        logger.error(f"Error creating free account: {str(e)}")
        return FreeAccountResponse(
            success=False,
            error="Failed to create account. Please try again."
        )


@router.post("/cancel-subscription")
async def cancel_subscription(
    request: CancelSubscriptionRequest,
    db: DatabaseAdapter = Depends(get_db)
):
    """
    Cancel a Stripe subscription
    """
    try:
        if not stripe.api_key or stripe.api_key == "":
            raise HTTPException(status_code=500, detail="Payment system not configured")

        # Cancel the subscription
        subscription = stripe.Subscription.delete(request.subscription_id)

        # Update database
        await db.execute(
            """
            UPDATE users
            SET subscription_plan = 'free', subscription_id = NULL
            WHERE subscription_id = $1
            """,
            request.subscription_id
        )

        logger.info(f"Subscription cancelled: {request.subscription_id}")

        return {
            "success": True,
            "message": "Subscription cancelled successfully",
            "status": subscription.status
        }

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error cancelling subscription: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error cancelling subscription: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")


@router.post("/webhook")
async def stripe_webhook(request: dict):
    """
    Stripe webhook endpoint for handling events
    """
    # TODO: Implement webhook signature verification
    # endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = request

        # Handle different event types
        if event['type'] == 'invoice.payment_succeeded':
            logger.info(f"Payment succeeded: {event['data']['object']['id']}")

        elif event['type'] == 'invoice.payment_failed':
            logger.warning(f"Payment failed: {event['data']['object']['id']}")

        elif event['type'] == 'customer.subscription.deleted':
            subscription_id = event['data']['object']['id']
            # Update database to reflect cancelled subscription
            logger.info(f"Subscription deleted: {subscription_id}")

        return {"received": True}

    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        raise HTTPException(status_code=400, detail="Webhook processing failed")


@router.get("/subscription/{user_id}")
async def get_subscription(user_id: str, db: DatabaseAdapter = Depends(get_db)):
    """
    Get subscription details for a user
    """
    try:
        result = await db.fetchone(
            """
            SELECT subscription_plan, subscription_id, stripe_customer_id, created_at
            FROM users
            WHERE id = $1
            """,
            user_id
        )

        if not result:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "user_id": user_id,
            "plan": result['subscription_plan'],
            "subscription_id": result['subscription_id'],
            "customer_id": result['stripe_customer_id'],
            "created_at": result['created_at']
        }

    except Exception as e:
        logger.error(f"Error fetching subscription: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch subscription details")
