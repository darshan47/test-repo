"""
VPC service layer — orchestrates EC2 provisioning and DAO persistence.

Each function receives a `VPCRepository` instance (injected by the router via
FastAPI's dependency system).  The service has no knowledge of which storage
backend is in use — DynamoDB, in-memory, or any future alternative.
"""

import logging
from typing import Optional

from app.cloud.ec2 import create_vpc_with_subnets
from app.dao.base import VPCRepository
from app.schemas.vpc import CreateVPCRequest, VPCResponse

logger = logging.getLogger(__name__)


def provision_vpc(
    request: CreateVPCRequest,
    created_by: str,
    repo: VPCRepository,
) -> VPCResponse:
    """
    Create a VPC + subnets in AWS and persist the record via the DAO.

    Parameters
    ----------
    request : CreateVPCRequest
        Validated request body from the caller.
    created_by : str
        Authenticated username — stored in the record for auditing.
    repo : VPCRepository
        DAO used to persist the resulting resource record.

    Returns
    -------
    VPCResponse
        Structured representation of the newly created resources.
    """
    subnets_payload = [s.model_dump() for s in request.subnets]

    logger.info(
        "User '%s' provisioning VPC '%s' (%s) with %d subnet(s).",
        created_by,
        request.vpc_name,
        request.vpc_cidr,
        len(subnets_payload),
    )

    record = create_vpc_with_subnets(
        vpc_cidr=request.vpc_cidr,
        subnets=subnets_payload,
        vpc_name=request.vpc_name,
        tags=request.tags,
        created_by=created_by,
    )

    repo.save(record)

    logger.info("VPC '%s' provisioned and persisted.", record["vpc_id"])
    return VPCResponse(**record)


def fetch_vpc(vpc_id: str, repo: VPCRepository) -> Optional[VPCResponse]:
    """
    Retrieve a VPC record by id from the DAO.

    Returns ``None`` when no matching record exists.
    """
    record = repo.get(vpc_id)
    if record is None:
        return None
    return VPCResponse(**record)


def fetch_all_vpcs(repo: VPCRepository) -> list[VPCResponse]:
    """Return all stored VPC records."""
    return [VPCResponse(**r) for r in repo.list_all()]


def remove_vpc_record(vpc_id: str, repo: VPCRepository) -> bool:
    """
    Delete a VPC record via the DAO (does NOT touch the real AWS VPC).

    Returns ``True`` if the record existed and was deleted.
    """
    return repo.delete(vpc_id)
