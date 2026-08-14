from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET


@csrf_exempt
@require_GET
def liveness(_request):
    """Process is up. Used by Docker / k8s liveness probes."""
    return JsonResponse({"status": "ok", "checks": {"app": "ok"}})


@csrf_exempt
@require_GET
def readiness(_request):
    """Dependencies are reachable. Used by readiness probes."""
    checks = {"app": "ok"}
    status_code = 200
    try:
        connection.ensure_connection()
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = str(exc)
        status_code = 503
    try:
        cache.set("healthcheck", "1", 5)
        if cache.get("healthcheck") != "1":
            raise RuntimeError("cache miss")
        checks["cache"] = "ok"
    except Exception as exc:
        checks["cache"] = str(exc)
        status_code = 503
    return JsonResponse({"status": "ok" if status_code == 200 else "degraded", "checks": checks}, status=status_code)
