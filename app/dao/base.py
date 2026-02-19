"""
Abstract DAO (Data Access Object) for VPC records.

`VPCRepository` defines the persistence contract that the service layer depends
on.  Concrete implementations (DynamoDB, in-memory for tests, …) must fulfil
this interface without the service or router knowing which backend is in use.

Why ABC instead of Protocol?
────────────────────────────
`ABC` + `abstractmethod` gives us runtime enforcement — instantiating a
subclass that hasn't implemented every method raises `TypeError` immediately,
making missing implementations obvious during development rather than at
call-time.  Use `Protocol` if you prefer structural (duck-typed) checking.
"""

from abc import ABC, abstractmethod
from typing import Optional


class VPCRepository(ABC):
    """Persistence interface for VPC resource records."""

    @abstractmethod
    def save(self, record: dict) -> None:
        """
        Persist a VPC record.

        Parameters
        ----------
        record : dict
            The full VPC resource record to store.  Must contain a ``vpc_id``
            string key that serves as the unique identifier.
        """

    @abstractmethod
    def get(self, vpc_id: str) -> Optional[dict]:
        """
        Retrieve a single VPC record by its id.

        Returns ``None`` when no matching record is found.
        """

    @abstractmethod
    def list_all(self) -> list[dict]:
        """Return every stored VPC record."""

    @abstractmethod
    def delete(self, vpc_id: str) -> bool:
        """
        Delete the record with the given *vpc_id*.

        Returns ``True`` if the record existed and was removed,
        ``False`` if no matching record was found.
        """
