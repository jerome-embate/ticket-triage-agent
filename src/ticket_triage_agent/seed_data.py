# --- Fake "customer database" ---
fake_customers = {
    "cust_4471": {"name": "Maria Santos", "plan": "pro", "account_status": "active", "past_tickets": 2},
    "cust_5502": {"name": "John Reyes", "plan": "free", "account_status": "active", "past_tickets": 0},
    "cust_6103": {"name": "Anna Cruz", "plan": "enterprise", "account_status": "suspended", "past_tickets": 5},
}

# --- Fake "known issues" list (e.g. an ongoing outage) ---
known_issues = [
    {"issue_id": "INC-201", "description": "Dashboard 500 errors for pro-tier users", "status": "investigating"},
]

# --- Knowledge base articles (source for RAG) ---
kb_articles = [
    """To reset your password, go to Settings > Security > Reset Password. 
    You'll receive an email with a reset link valid for 24 hours. If you don't 
    receive the email, check your spam folder or contact support to verify your 
    account email address.""",

    """Billing charges are processed on the 1st of each month for all active 
    subscriptions. If you're on the Pro plan and see a duplicate charge, this is 
    usually due to a failed payment retry. Refunds for duplicate charges are 
    processed automatically within 3-5 business days.""",

    """The Free plan includes up to 100 API calls per day. If you exceed this 
    limit, requests will return a 429 error until the daily quota resets at 
    midnight UTC. Upgrading to Pro removes this limit entirely.""",

    """If you're experiencing a 500 error on the dashboard, this is often caused 
    by a temporary server issue. Check our status page first. If the issue 
    persists for more than 15 minutes, it may be an active incident affecting 
    multiple users.""",

    """To cancel your subscription, go to Settings > Billing > Cancel Plan. 
    Cancellations take effect at the end of the current billing cycle, and you 
    retain access until then. There are no cancellation fees.""",
]


# --- Golden dataset for evaluation ---
golden_tickets = [
    {
        "ticket_id": "T-1001",
        "customer_id": "cust_4471",
        "subject": "Can't access my dashboard",
        "body": "I keep getting a 500 error when I try to log in to my dashboard.",
        "expected_category": "technical",
        "expected_urgency": "high",
    },
    {
        "ticket_id": "T-1002",
        "customer_id": "cust_5502",
        "subject": "Getting rate limited",
        "body": "My API calls are returning 429 errors, is there a daily limit?",
        "expected_category": "technical",
        "expected_urgency": "low",
    },
    {
        "ticket_id": "T-1003",
        "customer_id": "cust_4471",
        "subject": "Charged twice this month",
        "body": "I see two charges on my card for this month's subscription, please help.",
        "expected_category": "billing",
        "expected_urgency": "medium",
    },
    {
        "ticket_id": "T-1004",
        "customer_id": "cust_6103",
        "subject": "How do I cancel?",
        "body": "I want to cancel my subscription, what's the process?",
        "expected_category": "billing",
        "expected_urgency": "low",
    },
    {
        "ticket_id": "T-1005",
        "customer_id": "cust_5502",
        "subject": "Feature idea",
        "body": "It would be great if you could add dark mode to the dashboard.",
        "expected_category": "feature_request",
        "expected_urgency": "low",
    },
]