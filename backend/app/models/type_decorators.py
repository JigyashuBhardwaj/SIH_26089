"""
Small helper for the locked "Python enum.Enum, persisted as VARCHAR +
CHECK constraint, never a native PostgreSQL ENUM type" decision.

`sqlalchemy.Enum(..., native_enum=False)` is SQLAlchemy's own built-in way
to get exactly that: a VARCHAR column plus a `CHECK (col IN (...))`
constraint enumerating the allowed values, with no `CREATE TYPE ... AS
ENUM` and none of the "ALTER TYPE ... ADD VALUE" friction that comes with
a real Postgres enum type. `values_callable` makes SQLAlchemy store each
member's `.value` (e.g. "ASSOCIATION_ADMIN") rather than its `.name`,
which is a no-op for these particular enums (name == value everywhere)
but keeps the column's on-disk representation defined by the enum's
values rather than an implementation detail of Python's `Enum`.
"""

from enum import Enum
from typing import TypeVar

from sqlalchemy import Enum as SAEnum

E = TypeVar("E", bound=Enum)


def str_enum_column(enum_cls: type[E], *, name: str) -> SAEnum:
    """
    Build a VARCHAR+CHECK column type for a str-valued Python enum.

    `create_constraint=True` is required and easy to miss: as of
    SQLAlchemy 2.0, `Enum(..., native_enum=False)` alone renders a plain
    VARCHAR column with NO database-level CHECK constraint (the default
    flipped away from creating one, to avoid surprising users who only
    wanted `native_enum=False` for portability, not enforcement). Without
    it, invalid status/role strings would be silently accepted by
    PostgreSQL and only rejected by Python-side validation — which fails
    the locked "VARCHAR + CHECK" requirement. Verified empirically: a
    real migration run without `create_constraint=True` produced a
    `status` column with no corresponding `pg_constraint` row.
    """
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda cls: [member.value for member in cls],
    )
