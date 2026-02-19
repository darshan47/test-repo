"""
Pydantic schemas for the VPC API endpoints.

Separating request/response models from route logic keeps routes thin and
makes the OpenAPI docs (Swagger UI) accurate and self-documenting.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator
import ipaddress


# ── Request models ────────────────────────────────────────────────────────────

class SubnetRequest(BaseModel):
    """A single subnet to be created inside the VPC."""

    cidr: str = Field(
        ...,
        examples=["10.0.1.0/24"],
        description="IPv4 CIDR block for the subnet.",
    )
    az: str = Field(
        ...,
        examples=["us-east-1a"],
        description="Availability zone where the subnet will be created.",
    )
    name: Optional[str] = Field(
        None,
        examples=["public-subnet-1"],
        description="Human-readable name tag (auto-generated if omitted).",
    )

    @field_validator("cidr")
    @classmethod
    def validate_cidr(cls, v: str) -> str:
        try:
            ipaddress.IPv4Network(v, strict=False)
        except ValueError:
            raise ValueError(f"'{v}' is not a valid IPv4 CIDR block.")
        return v


class CreateVPCRequest(BaseModel):
    """Request body for POST /vpc."""

    vpc_cidr: str = Field(
        ...,
        examples=["10.0.0.0/16"],
        description="IPv4 CIDR block for the VPC.",
    )
    vpc_name: str = Field(
        "my-vpc",
        examples=["production-vpc"],
        description="Name tag applied to the VPC and all child resources.",
    )
    subnets: list[SubnetRequest] = Field(
        ...,
        min_length=1,
        description="One or more subnets to create inside the VPC.",
    )
    tags: Optional[dict[str, str]] = Field(
        None,
        examples=[{"Environment": "production", "Team": "platform"}],
        description="Additional AWS resource tags applied to every created resource.",
    )

    @field_validator("vpc_cidr")
    @classmethod
    def validate_vpc_cidr(cls, v: str) -> str:
        try:
            net = ipaddress.IPv4Network(v, strict=False)
            # Practical minimum for a VPC is /28; AWS max is /16
            if net.prefixlen > 28 or net.prefixlen < 16:
                raise ValueError("VPC CIDR prefix must be between /16 and /28.")
        except ValueError as exc:
            raise ValueError(str(exc))
        return v


# ── Response models ───────────────────────────────────────────────────────────

class SubnetDetail(BaseModel):
    subnet_id: str
    cidr: str
    availability_zone: str
    name: str


class VPCResponse(BaseModel):
    """Returned after a successful VPC creation or retrieval."""

    vpc_id: str
    vpc_name: str
    vpc_cidr: str
    igw_id: Optional[str] = None
    region: str
    subnets: list[SubnetDetail]
    tags: Optional[dict[str, str]] = None
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    status: Optional[str] = None


class VPCListResponse(BaseModel):
    """Returned by GET /vpc (list all)."""

    count: int
    vpcs: list[VPCResponse]
