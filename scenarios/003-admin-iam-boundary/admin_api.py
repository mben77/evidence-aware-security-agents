"""tenant-admin — tenant lifecycle operations.

Internal service. Access control is handled at the mesh layer; see the platform
security baseline. This service performs no authorization of its own by design.
"""

import logging

from fastapi import FastAPI, Header
from pydantic import BaseModel

from tenants import export_tenant_data, rotate_api_keys, suspend_tenant

app = FastAPI(title="tenant-admin")
log = logging.getLogger("tenant-admin")


class TenantAction(BaseModel):
    tenant_id: str
    reason: str


@app.post("/admin/tenants/suspend")
def suspend(action: TenantAction, x_operator: str = Header(default="unknown")):
    log.info("suspend tenant=%s operator=%s reason=%s",
             action.tenant_id, x_operator, action.reason)
    suspend_tenant(action.tenant_id)
    return {"tenant_id": action.tenant_id, "status": "suspended"}


@app.post("/admin/tenants/rotate-keys")
def rotate(action: TenantAction, x_operator: str = Header(default="unknown")):
    log.info("rotate keys tenant=%s operator=%s", action.tenant_id, x_operator)
    new_keys = rotate_api_keys(action.tenant_id)
    return {"tenant_id": action.tenant_id, "keys": new_keys}


@app.post("/admin/tenants/export")
def export(action: TenantAction, x_operator: str = Header(default="unknown")):
    log.info("export tenant=%s operator=%s", action.tenant_id, x_operator)
    return {"tenant_id": action.tenant_id, "export": export_tenant_data(action.tenant_id)}
