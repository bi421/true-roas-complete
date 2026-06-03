from fastapi import Depends, HTTPException, status, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from src.trueroas.core.config import settings

security = HTTPBearer()

async def get_current_tenant(request: Request, auth: HTTPAuthorizationCredentials = Security(security)) -> str:
    """
    Decodes JWT and validates tenant context.
    In production, this verifies the 'tenant_id' claim.
    """
    try:
        payload = jwt.decode(auth.credentials, settings.APP_SECRET_SALT, algorithms=["HS256"])
        tenant_id: str = payload.get("tenant_id")
        if not tenant_id:
            raise HTTPException(status_code=403, detail="Invalid tenant context in token")

        # Security Audit: Detect and block mismatched tenant contexts (IDOR prevention)
        header_tenant_id = request.headers.get("X-Tenant-ID")
        if header_tenant_id and header_tenant_id != tenant_id:
            # Aligned with Audit SQL requirements: request_method, endpoint, tenant_ids
            request.state.logger.critical("cross_tenant_access_attempt", extra={
                "tenant_id_authenticated": tenant_id,
                "tenant_id_requested": header_tenant_id,
                "request_method": request.method,
                "endpoint": request.url.path,
                "severity": "CRITICAL"
            })
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context mismatch")

        return tenant_id
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

async def require_admin(request: Request, auth: HTTPAuthorizationCredentials = Security(security)):
    """Enforces admin-level permissions."""
    try:
        payload = jwt.decode(auth.credentials, settings.APP_SECRET_SALT, algorithms=["HS256"])
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin privileges required")

        # Requirement: Audit successful administrative cross-tenant access
        header_tenant_id = request.headers.get("X-Tenant-ID")
        if header_tenant_id:
            request.state.logger.info("cross_tenant_access_success", extra={
                "tenant_id_authenticated": f"admin:{payload.get('sub')}",
                "tenant_id_requested": header_tenant_id,
                "request_method": request.method,
                "endpoint": request.url.path,
                "response_status": 200
            })
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid credentials")