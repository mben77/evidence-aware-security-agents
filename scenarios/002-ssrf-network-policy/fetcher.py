"""webhook-preview — fetches a customer-supplied URL and returns a preview."""

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="webhook-preview")

TIMEOUT_SECONDS = 5.0
MAX_PREVIEW_BYTES = 8192


class PreviewRequest(BaseModel):
    url: str


@app.post("/internal/v1/webhooks/preview")
def preview(req: PreviewRequest):
    """Fetch the customer's webhook URL and return a truncated preview.

    The URL is supplied by the customer through the product UI. We deliberately
    allow arbitrary hosts here because customers legitimately point webhooks at
    self-hosted endpoints, including ones on non-standard ports.
    """
    if not req.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="url must be http or https")

    try:
        with httpx.Client(timeout=TIMEOUT_SECONDS, follow_redirects=True) as client:
            response = client.get(req.url)
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"fetch failed: {exc}")

    body = response.content[:MAX_PREVIEW_BYTES]
    return {
        "status_code": response.status_code,
        "headers": dict(response.headers),
        "body_preview": body.decode("utf-8", errors="replace"),
    }
