"""
Application configuration loaded from environment variables.
Uses pydantic-settings so every value can be overridden via a .env file.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── JWT ──────────────────────────────────────────────────────────────────
    # Secret used to sign/verify JWT tokens.  Change this in production!
    jwt_secret_key: str = "changeme-super-secret-key"
    jwt_algorithm: str = "HS256"
    # Token lifetime in minutes
    jwt_expire_minutes: int = 60

    # ── Demo users ────────────────────────────────────────────────────────────
    # Comma-separated list of "username:password" pairs used for the built-in
    # credential store.  In production replace with a real identity provider
    # (e.g. Amazon Cognito).
    demo_users: str = "admin:secret,user1:password1"

    # ── AWS ──────────────────────────────────────────────────────────────────
    aws_region: str = "us-east-1"
    # Leave blank to use the default credential chain (IAM role, env vars, …)
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # ── DynamoDB ─────────────────────────────────────────────────────────────
    dynamodb_table_name: str = "vpc_resources"
    # Set to a local DynamoDB endpoint for development (e.g. http://localhost:8000)
    dynamodb_endpoint_url: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    # ── Helpers ───────────────────────────────────────────────────────────────
    def get_demo_users(self) -> dict[str, str]:
        """Return the demo user map {username: password}."""
        users: dict[str, str] = {}
        for pair in self.demo_users.split(","):
            pair = pair.strip()
            if ":" in pair:
                username, password = pair.split(":", 1)
                users[username.strip()] = password.strip()
        return users


settings = Settings()
