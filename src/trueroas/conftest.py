import os
import sys
from typing import Any, Iterator

import pytest


def pytest_sessionstart(session: Any) -> None:  # pragma: no cover
    """Ensure `import trueroas` works when pytest isn't run with PYTHONPATH."""

    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    src_path = os.path.join(repo_root, "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


@pytest.fixture(autouse=True, scope="session")
def _ensure_central_tables() -> Iterator[None]:
    """Create central DB tables before tests.

    Fixes: sqlite3.OperationalError: no such table: tenants
    """

    from trueroas.core.database import Base as CentralBase
    from trueroas.core.database import central_engine

    # Ensure model modules are imported so SQLAlchemy metadata is populated.
    from trueroas.core import subscriptions as _subscriptions  # noqa: F401

    CentralBase.metadata.create_all(bind=central_engine)

    yield

