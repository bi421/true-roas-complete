from fastapi import HTTPException, status, Security, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from src.trueroas.core.config import settings
import logging
from typing import Any, cast

security = HTTPBearer()
logger = logging.getLogger("trueroas.auth")


async def get_auth_context(
    request: Request, auth: HTTPAuthorizationCredentials = Security(security)
) -> dict[str, Any]:
    """
    Decodes JWT and validates tenant context.
    In production, this verifies the 'tenant_id' claim.
    """
    try:
        # 2026 Standard: Verify expiration and audience to prevent replay attacks
        payload = jwt.decode(
            auth.credentials,
            settings.APP_SECRET_SALT,
            algorithms=["HS256"],
            options={"verify_exp": True, "verify_aud": True},
            audience="trueroas-api",
        )
        tenant_id = cast(str, payload.get("tenant_id"))
        if not tenant_id:
            raise HTTPException(
                status_code=403, detail="Invalid tenant context in token"
            )

        # Security Audit: Detect and block mismatched tenant contexts (IDOR prevention)
        header_tenant_id = request.headers.get("X-Tenant-ID")
        if header_tenant_id and header_tenant_id != tenant_id:
            # Log critical error to system logs
            logger.critical(
                "cross_tenant_access_attempt",
                extra={
                    "tenant_id_authenticated": tenant_id,
                    "tenant_id_requested": header_tenant_id,
                    "request_method": request.method,
                    "endpoint": request.url.path,
                    "severity": "CRITICAL",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context mismatch"
            )

        return cast(dict[str, Any], payload)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


async def get_current_tenant(
    payload: dict[str, Any] = Depends(get_auth_context),
) -> str:
    return cast(str, payload.get("tenant_id"))


async def require_admin(
    request: Request, auth: HTTPAuthorizationCredentials = Security(security)
) -> None:
    """Enforces admin-level permissions."""
    try:
        payload = jwt.decode(
            auth.credentials,
            settings.APP_SECRET_SALT,
            algorithms=["HS256"],
            options={"verify_exp": True, "verify_aud": True},
            audience="trueroas-api",
        )
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin privileges required")

        # Logging through structured state logger
        header_tenant_id = request.headers.get("X-Tenant-ID")
        if header_tenant_id and hasattr(request.state, "logger"):
            request.state.logger.info(
                "admin_access_granted", extra={"tenant": header_tenant_id}
            )

    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid credentials")
