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
