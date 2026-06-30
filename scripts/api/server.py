"""Run the API with environment-controlled production settings."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    uvicorn.run(
        "scripts.api.app:app",
        host=os.getenv("SUSBIOME_HOST", "0.0.0.0"),
        port=int(os.getenv("SUSBIOME_PORT", "8000")),
        workers=int(os.getenv("SUSBIOME_WEB_CONCURRENCY", "1")),
        proxy_headers=os.getenv("SUSBIOME_PROXY_HEADERS", "false").lower() == "true",
        server_header=False,
    )


if __name__ == "__main__":
    main()
