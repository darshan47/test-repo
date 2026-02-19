"""Simple application configuration (defaults only)."""

# ── JWT ──────────────────────────────────────────────────────────────────────
# Secret used to sign/verify JWT tokens. Change this in production!
JWT_SECRET_KEY = "changeme-super-secret-key"
JWT_ALGORITHM = "HS256"
# Token lifetime in minutes
JWT_EXPIRE_MINUTES = 60

# ── Demo users ───────────────────────────────────────────────────────────────
# Comma-separated list of "username:password" pairs used for the built-in
# credential store. In production replace with a real identity provider.
DEMO_USERS = "admin:secret,user1:password1"

# ── AWS ──────────────────────────────────────────────────────────────────────
AWS_REGION = "us-east-1"
# Leave blank to use the default credential chain (IAM role, env vars, …)
AWS_ACCESS_KEY_ID = ""
AWS_SECRET_ACCESS_KEY = ""

# ── DynamoDB ────────────────────────────────────────────────────────────────
DYNAMODB_TABLE_NAME = "vpc_resources"
# Set to a local DynamoDB endpoint for development (e.g. http://localhost:8000)
DYNAMODB_ENDPOINT_URL = ""


def get_demo_users() -> dict[str, str]:
    """Return the demo user map {username: password}."""
    users: dict[str, str] = {}
    for pair in DEMO_USERS.split(","):
        pair = pair.strip()
        if ":" in pair:
            username, password = pair.split(":", 1)
            users[username.strip()] = password.strip()
    return users
