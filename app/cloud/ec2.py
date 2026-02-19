"""
EC2 helper — creates a VPC with one or more subnets.

Each call to `create_vpc_with_subnets` does the following in AWS:
  1. Create a VPC with the given CIDR block.
  2. Enable DNS hostnames on the VPC (best practice for EC2 / EKS workloads).
  3. Create an Internet Gateway and attach it to the VPC.
  4. Create each requested subnet in the specified availability zone.
  5. Apply any caller-supplied tags to every resource.

Returns a structured dict that can be persisted to DynamoDB and returned
to the API caller.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from app.config import settings

logger = logging.getLogger(__name__)


def _ec2_client():
    """Build a boto3 EC2 client from application settings."""
    kwargs = {"region_name": settings.aws_region}
    if settings.aws_access_key_id:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    return boto3.client("ec2", **kwargs)


def _tag_specs(resource_type: str, name: str, extra_tags: dict) -> list:
    """Build a TagSpecifications list understood by the EC2 API."""
    tags = [{"Key": "Name", "Value": name}]
    tags += [{"Key": k, "Value": v} for k, v in extra_tags.items()]
    return [{"ResourceType": resource_type, "Tags": tags}]


def create_vpc_with_subnets(
    vpc_cidr: str,
    subnets: list[dict],
    vpc_name: str = "my-vpc",
    tags: Optional[dict] = None,
    created_by: str = "api",
) -> dict:
    """
    Create a VPC together with the requested subnets.

    Parameters
    ----------
    vpc_cidr : str
        IPv4 CIDR block for the VPC, e.g. ``"10.0.0.0/16"``.
    subnets : list[dict]
        Each entry must have:
          - ``cidr``  (str)  — subnet CIDR, e.g. ``"10.0.1.0/24"``
          - ``az``    (str)  — availability zone, e.g. ``"us-east-1a"``
          - ``name``  (str, optional) — human-readable name tag
    vpc_name : str
        Name tag applied to the VPC and IGW.
    tags : dict, optional
        Additional key/value tags applied to all resources.
    created_by : str
        Username stored in the DynamoDB record for auditing.

    Returns
    -------
    dict
        Structured record with VPC id, IGW id, subnet details, timestamps, …
    """
    extra_tags = tags or {}
    ec2 = _ec2_client()

    # ── 1. Create VPC ─────────────────────────────────────────────────────────
    logger.info("Creating VPC with CIDR %s", vpc_cidr)
    try:
        vpc_resp = ec2.create_vpc(
            CidrBlock=vpc_cidr,
            TagSpecifications=_tag_specs("vpc", vpc_name, extra_tags),
        )
    except ClientError as exc:
        logger.error("Failed to create VPC: %s", exc)
        raise

    vpc_id = vpc_resp["Vpc"]["VpcId"]
    logger.info("VPC created: %s", vpc_id)

    # ── 2. Enable DNS hostnames ───────────────────────────────────────────────
    ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={"Value": True})
    ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsSupport={"Value": True})

    # ── 3. Internet Gateway ───────────────────────────────────────────────────
    igw_resp = ec2.create_internet_gateway(
        TagSpecifications=_tag_specs("internet-gateway", f"{vpc_name}-igw", extra_tags)
    )
    igw_id = igw_resp["InternetGateway"]["InternetGatewayId"]
    ec2.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
    logger.info("Internet Gateway %s attached to VPC %s", igw_id, vpc_id)

    # ── 4. Create subnets ─────────────────────────────────────────────────────
    created_subnets: list[dict] = []
    for idx, subnet_spec in enumerate(subnets):
        subnet_name = subnet_spec.get("name") or f"{vpc_name}-subnet-{idx + 1}"
        logger.info("Creating subnet %s in %s", subnet_spec["cidr"], subnet_spec["az"])
        try:
            sn_resp = ec2.create_subnet(
                VpcId=vpc_id,
                CidrBlock=subnet_spec["cidr"],
                AvailabilityZone=subnet_spec["az"],
                TagSpecifications=_tag_specs("subnet", subnet_name, extra_tags),
            )
        except ClientError as exc:
            logger.error("Failed to create subnet %s: %s", subnet_spec["cidr"], exc)
            # Attempt best-effort cleanup of already-created resources
            _cleanup_on_error(ec2, vpc_id, igw_id, [s["subnet_id"] for s in created_subnets])
            raise

        subnet_id = sn_resp["Subnet"]["SubnetId"]
        created_subnets.append(
            {
                "subnet_id": subnet_id,
                "cidr": subnet_spec["cidr"],
                "availability_zone": subnet_spec["az"],
                "name": subnet_name,
            }
        )
        logger.info("Subnet created: %s", subnet_id)

    # ── 5. Build and return result record ─────────────────────────────────────
    return {
        "vpc_id": vpc_id,
        "vpc_name": vpc_name,
        "vpc_cidr": vpc_cidr,
        "igw_id": igw_id,
        "region": settings.aws_region,
        "subnets": created_subnets,
        "tags": extra_tags,
        "created_by": created_by,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
    }


def _cleanup_on_error(ec2, vpc_id: str, igw_id: str, subnet_ids: list[str]) -> None:
    """Best-effort rollback on partial failure — logs but does not re-raise."""
    logger.warning("Rolling back resources due to error …")
    for subnet_id in subnet_ids:
        try:
            ec2.delete_subnet(SubnetId=subnet_id)
            logger.info("Deleted subnet %s", subnet_id)
        except ClientError as exc:
            logger.error("Could not delete subnet %s: %s", subnet_id, exc)

    try:
        ec2.detach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
        ec2.delete_internet_gateway(InternetGatewayId=igw_id)
        logger.info("Deleted IGW %s", igw_id)
    except ClientError as exc:
        logger.error("Could not delete IGW %s: %s", igw_id, exc)

    try:
        ec2.delete_vpc(VpcId=vpc_id)
        logger.info("Deleted VPC %s", vpc_id)
    except ClientError as exc:
        logger.error("Could not delete VPC %s: %s", vpc_id, exc)


def get_vpc_details(vpc_id: str) -> dict:
    """
    Fetch live VPC and subnet details directly from AWS.

    Returns a dict with the same shape as the DynamoDB record so callers
    can refresh stale persisted data.
    """
    ec2 = _ec2_client()

    try:
        vpc_resp = ec2.describe_vpcs(VpcIds=[vpc_id])
        vpc = vpc_resp["Vpcs"][0]
    except (ClientError, IndexError) as exc:
        logger.error("VPC %s not found in AWS: %s", vpc_id, exc)
        raise

    # Fetch subnets belonging to this VPC
    sn_resp = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])
    subnets = [
        {
            "subnet_id": sn["SubnetId"],
            "cidr": sn["CidrBlock"],
            "availability_zone": sn["AvailabilityZone"],
            "name": next(
                (t["Value"] for t in sn.get("Tags", []) if t["Key"] == "Name"), ""
            ),
        }
        for sn in sn_resp["Subnets"]
    ]

    name_tag = next(
        (t["Value"] for t in vpc.get("Tags", []) if t["Key"] == "Name"), vpc_id
    )
    return {
        "vpc_id": vpc_id,
        "vpc_name": name_tag,
        "vpc_cidr": vpc["CidrBlock"],
        "state": vpc["State"],
        "region": settings.aws_region,
        "subnets": subnets,
    }
