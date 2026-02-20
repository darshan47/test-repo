# ── JWT ──────────────────────────────────────────────────────────────────────
JWT_SECRET_KEY = "changeme-super-secret-key"
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60
DEMO_USERS = "admin:secret,user1:password1"

# ── AWS ──────────────────────────────────────────────────────────────────────
AWS_REGION = "us-east-1"
AWS_ACCESS_KEY_ID = ""
AWS_SECRET_ACCESS_KEY = ""

DYNAMODB_TABLE_NAME = "vpc_resources"
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
