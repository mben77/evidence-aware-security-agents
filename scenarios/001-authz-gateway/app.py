"""statements-service — account statement retrieval.

Runs behind the platform API gateway. Listens on the cluster network only.
"""

import os

from fastapi import FastAPI, Header, HTTPException

from db import fetch_statements, get_account

app = FastAPI(title="statements-service")

SERVICE_PORT = int(os.environ.get("PORT", "8080"))


@app.get("/api/v1/accounts/{account_id}/statements")
def list_statements(account_id: str, x_user_id: str = Header(...)):
    """Return statements for an account.

    The gateway authenticates the caller and forwards the resolved customer
    identity in X-User-Id.
    """
    account = get_account(account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="account not found")

    statements = fetch_statements(account_id)
    return {
        "account_id": account_id,
        "count": len(statements),
        "statements": statements,
    }


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
