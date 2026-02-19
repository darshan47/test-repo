"""
DEPRECATED — this module is no longer used by the application.

All DynamoDB logic has been moved to the DAO layer:
  app/dao/dynamodb_repository.py   ← DynamoDBVPCRepository (concrete impl)
  app/dao/base.py                  ← VPCRepository (abstract interface)

This file is kept temporarily to avoid breaking any external scripts that
may still import from it.  It will be removed in a future clean-up.
"""
