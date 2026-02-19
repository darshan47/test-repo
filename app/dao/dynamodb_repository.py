"""
DynamoDB implementation of VPCRepository.

All DynamoDB-specific concerns live here — boto3 client setup, table
bootstrapping, pagination — keeping the service layer storage-agnostic.

Table schema
────────────
  Table name    : vpc_resources  (configurable via DYNAMODB_TABLE_NAME)
  Partition key : vpc_id  (String)

The table is created automatically on first use when it does not already
exist.  In production, prefer managing the table via CloudFormation / SAM /
Terraform and removing the auto-create logic.
"""

import logging
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from app import config
from app.dao.base import VPCRepository

logger = logging.getLogger(__name__)


class DynamoDBVPCRepository(VPCRepository):
    """
    VPCRepository backed by Amazon DynamoDB.

    The instance is lightweight — the boto3 resource and table handle are
    created lazily on first use so that importing this module does not
    immediately require live AWS credentials.
    """

    def __init__(self) -> None:
        self._table = None  # populated on first access via _get_table()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _build_resource(self):
        """Create a boto3 DynamoDB resource from application settings."""
        kwargs: dict = {"region_name": config.AWS_REGION}
        if config.AWS_ACCESS_KEY_ID:
            kwargs["aws_access_key_id"] = config.AWS_ACCESS_KEY_ID
            kwargs["aws_secret_access_key"] = config.AWS_SECRET_ACCESS_KEY
        if config.DYNAMODB_ENDPOINT_URL:
            # Enables local DynamoDB (e.g. `dynamodb-local` container)
            kwargs["endpoint_url"] = config.DYNAMODB_ENDPOINT_URL
        return boto3.resource("dynamodb", **kwargs)

    def _get_table(self):
        """
        Return the DynamoDB Table handle, creating the table if it does not
        yet exist.  The handle is cached after the first successful call.
        """
        if self._table is not None:
            return self._table

        ddb = self._build_resource()
        table_name = config.DYNAMODB_TABLE_NAME

        try:
            table = ddb.create_table(
                TableName=table_name,
                KeySchema=[{"AttributeName": "vpc_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "vpc_id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            table.wait_until_exists()
            logger.info("DynamoDB table '%s' created.", table_name)
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ResourceInUseException":
                # Table already exists — reuse it
                table = ddb.Table(table_name)
            else:
                raise

        self._table = table
        return self._table

    # ── VPCRepository interface ───────────────────────────────────────────────

    def save(self, record: dict) -> None:
        """
        Write *record* to DynamoDB using a PutItem call.

        An existing item with the same ``vpc_id`` is completely replaced.
        """
        table = self._get_table()
        try:
            table.put_item(Item=record)
            logger.info("Saved VPC record for '%s'.", record.get("vpc_id"))
        except ClientError as exc:
            logger.error("DynamoDB PutItem failed: %s", exc)
            raise

    def get(self, vpc_id: str) -> Optional[dict]:
        """
        Fetch a single item from DynamoDB by primary key.

        Returns ``None`` when the item does not exist.
        """
        table = self._get_table()
        try:
            response = table.get_item(Key={"vpc_id": vpc_id})
            return response.get("Item")  # None if key not found
        except ClientError as exc:
            logger.error("DynamoDB GetItem failed for '%s': %s", vpc_id, exc)
            raise

    def list_all(self) -> list[dict]:
        """
        Scan the entire table and return all items.

        Handles DynamoDB pagination transparently — multiple Scan calls are
        issued until ``LastEvaluatedKey`` is absent from the response.

        Note: Scan reads every item in the table.  For large tables, consider
        adding a GSI and switching to Query.
        """
        table = self._get_table()
        try:
            response = table.scan()
            items: list[dict] = response.get("Items", [])

            while "LastEvaluatedKey" in response:
                response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
                items.extend(response.get("Items", []))

            logger.info("Listed %d VPC record(s) from DynamoDB.", len(items))
            return items
        except ClientError as exc:
            logger.error("DynamoDB Scan failed: %s", exc)
            raise

    def delete(self, vpc_id: str) -> bool:
        """
        Delete the item with *vpc_id* as primary key.

        ``ReturnValues="ALL_OLD"`` lets us detect whether the item actually
        existed before the delete, so we can return an accurate boolean.
        """
        table = self._get_table()
        try:
            response = table.delete_item(
                Key={"vpc_id": vpc_id},
                ReturnValues="ALL_OLD",
            )
            existed = bool(response.get("Attributes"))
            if existed:
                logger.info("Deleted DynamoDB record for VPC '%s'.", vpc_id)
            else:
                logger.warning("Delete called for non-existent VPC '%s'.", vpc_id)
            return existed
        except ClientError as exc:
            logger.error("DynamoDB DeleteItem failed for '%s': %s", vpc_id, exc)
            raise
