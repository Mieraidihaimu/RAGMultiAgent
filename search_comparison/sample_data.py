"""Sample dataset for search comparison."""
from typing import List, Dict, Any


def get_sample_documents() -> List[Dict[str, Any]]:
    """Sample documents for testing search scenarios."""
    return [
        {
            "id": "doc_001",
            "title": "Password Reset Guide",
            "content": "If you've forgotten your password, you can reset it by clicking the 'Forgot Password' link on the login page. Enter your email address and we'll send you a reset link.",
            "category": "authentication",
            "tags": ["password", "security", "login"],
            "created_at": "2024-01-15"
        },
        {
            "id": "doc_002",
            "title": "Two-Factor Authentication Setup",
            "content": "Enable 2FA to add an extra layer of security to your account. Go to Settings > Security > Two-Factor Authentication.",
            "category": "authentication",
            "tags": ["2fa", "security"],
            "created_at": "2024-01-20"
        },
        {
            "id": "doc_003",
            "title": "Login Troubleshooting",
            "content": "Can't access your account? Common issues include incorrect credentials, locked account, expired session, or disabled browser cookies.",
            "category": "authentication",
            "tags": ["login", "troubleshooting"],
            "created_at": "2024-02-01"
        },
        {
            "id": "doc_004",
            "title": "OAuth Integration",
            "content": "Our OAuth 2.0 implementation allows secure third-party access. Access tokens expire after 1 hour, refresh tokens after 30 days.",
            "category": "authentication",
            "tags": ["oauth", "api", "tokens"],
            "created_at": "2024-02-10"
        },
        {
            "id": "doc_005",
            "title": "Updating Account Credentials",
            "content": "To change your username, email, or password, navigate to Account Settings. Email changes require verification.",
            "category": "account",
            "tags": ["credentials", "settings"],
            "created_at": "2024-01-25"
        },
        {
            "id": "doc_006",
            "title": "Subscription Plans",
            "content": "We offer Basic ($9/month), Pro ($29/month), and Enterprise (custom pricing). All include 24/7 support.",
            "category": "billing",
            "tags": ["subscription", "pricing"],
            "created_at": "2024-01-10"
        },
        {
            "id": "doc_007",
            "title": "Refund Policy",
            "content": "30-day money-back guarantee for new subscribers. Contact support with your invoice number for refunds.",
            "category": "billing",
            "tags": ["refund", "money back"],
            "created_at": "2024-01-18"
        },
        {
            "id": "doc_008",
            "title": "API Rate Limits",
            "content": "Rate limits: Basic (100 req/hour), Pro (1000 req/hour), Enterprise (custom). Use exponential backoff for retries.",
            "category": "api",
            "tags": ["api", "rate limit"],
            "created_at": "2024-02-15"
        }
    ]


def get_test_queries() -> List[Dict[str, Any]]:
    """Test queries for different scenarios."""
    return [
        {
            "query": "password reset",
            "scenario": "exact_match",
            "relevant_docs": ["doc_001", "doc_003"],
            "description": "Exact keyword match"
        },
        {
            "query": "pasword resset",
            "scenario": "typos",
            "relevant_docs": ["doc_001"],
            "description": "Fuzzy matching for typos"
        },
        {
            "query": "I can't log in to my account",
            "scenario": "semantic_intent",
            "relevant_docs": ["doc_003", "doc_001"],
            "description": "Natural language understanding"
        },
        {
            "query": "change my credentials",
            "scenario": "synonyms",
            "relevant_docs": ["doc_005", "doc_001"],
            "description": "Synonym matching"
        }
    ]
