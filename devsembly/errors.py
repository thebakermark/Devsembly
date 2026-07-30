from __future__ import annotations


class GenesisError(Exception):
    """Base error for the Genesis application boundary."""


class ResourceNotFoundError(GenesisError):
    def __init__(self, resource: str) -> None:
        self.resource = resource
        super().__init__(f"{resource} was not found")


class DuplicateResourceError(GenesisError):
    def __init__(self, resource: str) -> None:
        self.resource = resource
        super().__init__(f"{resource} already exists")


class StaleVersionError(GenesisError):
    def __init__(self, resource: str, expected_version: int) -> None:
        self.resource = resource
        self.expected_version = expected_version
        super().__init__(
            f"{resource} changed after version {expected_version}; reload it and retry"
        )


class IdempotencyConflictError(GenesisError):
    def __init__(self, idempotency_key: str) -> None:
        self.idempotency_key = idempotency_key
        super().__init__(
            f"idempotency key {idempotency_key!r} was already used for a different request"
        )


class InvalidTransitionError(GenesisError):
    def __init__(self, resource: str, current_status: str, target_status: str) -> None:
        self.resource = resource
        self.current_status = current_status
        self.target_status = target_status
        super().__init__(
            f"{resource} cannot transition from {current_status!r} to {target_status!r}"
        )
