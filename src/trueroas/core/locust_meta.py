from typing import Any, Callable

try:
    import locust
except ModuleNotFoundError:
    locust = None

HttpUser: Any = None
task: Any = None

if locust is None:

    class _FallbackHttpUser:
        client = None

    def _fallback_task(func: Callable[..., Any]) -> Callable[..., Any]:
        return func

    HttpUser = _FallbackHttpUser
    task = _fallback_task
else:
    HttpUser = locust.HttpUser
    task = locust.task


class MetaSyncUser(HttpUser):  # type: ignore[misc]
    @task  # type: ignore[untyped-decorator]
    def sync(self) -> None:
        self.client.post("/api/v1/sync", json={"tenant_id": "test"})
