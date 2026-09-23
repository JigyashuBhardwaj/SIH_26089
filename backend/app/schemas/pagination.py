"""
Reusable pagination foundation for future list endpoints.

Nothing in this module is wired into any route yet — Phase 5E-A is
foundation only. Future domain list endpoints (e.g. listing workers or
service requests) are expected to depend on `PaginationParams` and return
a `PaginatedResponse[...]`, rather than each inventing its own bounds and
defaults.

Deliberately a simple bounded page/page_size convention, not cursor
pagination.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


class PaginationParams(BaseModel):
    """
    Bounded page/page_size query parameters for a future list endpoint.

    `page` is 1-indexed and must be positive. `page_size` defaults to
    `DEFAULT_PAGE_SIZE` and can never exceed `MAX_PAGE_SIZE`, so a client
    can't request an unbounded result set.
    """

    page: int = Field(default=1, ge=1, description="1-indexed page number.")
    page_size: int = Field(
        default=DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description=f"Items per page (max {MAX_PAGE_SIZE}).",
    )

    @property
    def offset(self) -> int:
        """SQL `OFFSET` value corresponding to this page/page_size."""
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response envelope for a future list endpoint."""

    items: list[T]
    page: int
    page_size: int
    total: int
