"""
VPC router — all endpoints under /vpc.

Every route requires a valid JWT (via the `get_current_user` dependency).
Authorization is open to all authenticated users — no additional role
checks are applied.

The VPCRepository is injected via `get_vpc_repository`.  Swapping the
storage backend (e.g. an in-memory repo for tests) only requires overriding
that single dependency — no route or service code changes are needed.

Endpoints
─────────
  POST   /vpc            Create a new VPC with subnets
  GET    /vpc            List all stored VPC records
  GET    /vpc/{vpc_id}   Get a single VPC record by id
  DELETE /vpc/{vpc_id}   Remove a VPC record from the store (not from AWS)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from botocore.exceptions import ClientError

from app.dependencies.api import get_current_user
from app.dao.base import VPCRepository
from app.dependencies.dao import get_vpc_repository
from app.schemas.vpc import CreateVPCRequest, VPCListResponse, VPCResponse
from app.services.vpc import fetch_all_vpcs, fetch_vpc, provision_vpc, remove_vpc_record

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vpc", tags=["VPC Management"])


@router.post(
    "",
    response_model=VPCResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a VPC with subnets",
    description=(
        "Creates an AWS VPC with the given CIDR block, attaches an Internet Gateway, "
        "and provisions each requested subnet. The resulting resource IDs are stored "
        "in DynamoDB and returned in the response."
    ),
)
def create_vpc(
    body: CreateVPCRequest,
    current_user: str = Depends(get_current_user),
    repo: VPCRepository = Depends(get_vpc_repository),
) -> VPCResponse:
    """Create a VPC + subnets and persist the record via the DAO."""
    logger.info("POST /vpc called by '%s'", current_user)
    try:
        return provision_vpc(request=body, created_by=current_user, repo=repo)
    except Exception as exc:
        logger.exception("VPC creation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AWS error: {exc}",
        ) from exc


@router.get(
    "",
    response_model=VPCListResponse,
    summary="List all VPC records",
    description="Returns every VPC record stored in DynamoDB.",
)
def list_vpcs(
    current_user: str = Depends(get_current_user),
    repo: VPCRepository = Depends(get_vpc_repository),
) -> VPCListResponse:
    """Return all stored VPC records."""
    logger.info("GET /vpc called by '%s'", current_user)
    vpcs = fetch_all_vpcs(repo=repo)
    return VPCListResponse(count=len(vpcs), vpcs=vpcs)


@router.get(
    "/{vpc_id}",
    response_model=VPCResponse,
    summary="Get a VPC record by id",
    description="Returns the stored record for the given VPC id.",
)
def get_vpc(
    vpc_id: str,
    current_user: str = Depends(get_current_user),
    repo: VPCRepository = Depends(get_vpc_repository),
) -> VPCResponse:
    """Retrieve a single VPC record."""
    logger.info("GET /vpc/%s called by '%s'", vpc_id, current_user)
    record = fetch_vpc(vpc_id=vpc_id, repo=repo)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VPC '{vpc_id}' not found.",
        )
    return record


@router.delete(
    "/{vpc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a VPC and its AWS resources",
    description=(
        "Deletes the AWS VPC resources (subnets, IGW, VPC) and then removes the stored record."
    ),
)
def delete_vpc(
    vpc_id: str,
    current_user: str = Depends(get_current_user),
    repo: VPCRepository = Depends(get_vpc_repository),
) -> None:
    """Delete AWS VPC resources and remove the stored record."""
    logger.info("DELETE /vpc/%s called by '%s'", vpc_id, current_user)
    try:
        deleted = remove_vpc_record(vpc_id=vpc_id, repo=repo)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"VPC '{vpc_id}' not found.",
            )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code == "DependencyViolation":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "VPC has dependent resources not created by this service. "
                    "Only resources created by this service are deleted; clean up the "
                    "remaining dependencies manually, then retry."
                ),
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AWS error: {exc}",
        ) from exc
