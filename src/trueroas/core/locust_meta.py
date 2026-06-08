# mypy: ignore-errors
from typing import Any

try:
    import locust
except ModuleNotFoundError:
    locust = None

HttpUser: Any
task: Any

if locust is None:

    class _FallbackHttpUser:
        client = None

    def _fallback_task(func):
        return func

    HttpUser = _FallbackHttpUser
    task = _fallback_task
else:
    HttpUser = locust.HttpUser
    task = locust.task


class MetaSyncUser(HttpUser):  # type: ignore[valid-type,misc]
    @task
    def sync(self):
        self.client.post("/api/v1/sync", json={"tenant_id": "test"})
