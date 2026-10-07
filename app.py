from __future__ import annotations
import contextlib
import os
from collections.abc import AsyncIterator
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from mcp.server.transport_security import TransportSecuritySettings
from server import mcp

VERSION = "1.1.0"

async def health(_request: Request) -> JSONResponse:
    return JSONResponse({"status":"ok","service":"Marcio Translation MCP","version":VERSION,"mcp_path":"/mcp"})

def _security() -> TransportSecuritySettings:
    hosts=[h.strip() for h in os.getenv("MCP_ALLOWED_HOSTS","").split(",") if h.strip()]
    origins=[o.strip() for o in os.getenv("MCP_ALLOWED_ORIGINS","").split(",") if o.strip()]
    if hosts:
        return TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=hosts,
            allowed_origins=origins,
        )
    # Intended for a trusted TLS-terminating reverse proxy such as Render.
    # ChatGPT calls the MCP endpoint server-to-server, so browser CORS is not required.
    return TransportSecuritySettings(enable_dns_rebinding_protection=False)

mcp_app = mcp.streamable_http_app(
    streamable_http_path="/mcp",
    stateless_http=True,
    json_response=True,
    transport_security=_security(),
)

@contextlib.asynccontextmanager
async def lifespan(_app: Starlette) -> AsyncIterator[None]:
    async with mcp.session_manager.run():
        yield

app = Starlette(
    routes=[Route("/health", health), Mount("/", app=mcp_app)],
    lifespan=lifespan,
)
