# Health Check

JAF provides a small health check utility for database connectivity checks. This is useful for Kubernetes liveness/readiness probes and monitoring.

## Python API

```python
from framework.health import check_health

result = await check_health()
# {
#   "status": "healthy" | "unhealthy",
#   "database": "ok" | "error",
#   "version": "...",
#   "details": {"database": "..."}  # only on failure
# }
```

## Example FastAPI endpoint

```python
from fastapi import FastAPI

from framework.health import check_health

app = FastAPI()


@app.get("/health")
async def health():
    # Return the framework health status as JSON.
    # You can also map "unhealthy" to HTTP 503 if desired.
    return await check_health()
```
