"""
FastAPI dependency for VPCRepository injection.

Routes declare `repo: VPCRepository = Depends(get_vpc_repository)` and
receive the concrete DynamoDB implementation at runtime.

Swapping the backend (e.g. for tests) only requires overriding this one
dependency — no service or route code changes are needed:

    app.dependency_overrides[get_vpc_repository] = lambda: InMemoryVPCRepository()
"""

from app.dao.base import VPCRepository
from app.dao.dynamodb import DynamoDBVPCRepository

# A single, module-level instance is sufficient — DynamoDBVPCRepository is
# stateless apart from the cached table handle, which is thread-safe.
_repository = DynamoDBVPCRepository()


def get_vpc_repository() -> VPCRepository:
    """Return the active VPCRepository implementation."""
    return _repository
