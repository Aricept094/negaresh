"""MCP adapter: registers the tools on the official low-level Server and hands raw
arguments to negaresh.api.

Two transports: stdio (local clients such as Claude Code, Claude Desktop, Cursor,
VS Code, Codex, Gemini CLI) and Streamable HTTP (remote clients such as ChatGPT).
Over HTTP the server also offers the read-only `search` and `fetch` pair that
ChatGPT connectors and deep research expect."""

from __future__ import annotations

import json
from typing import Any

import mcp_types as types
from mcp.server import CacheHint, Server, ServerRequestContext
from mcp.server.stdio import stdio_server

from . import __version__, api

SERVER_NAME = "negaresh"
REPO_URL = "https://github.com/Aricept094/negaresh"
_ANNOTATIONS = types.ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
_ENVELOPE_SCHEMA = {
    "type": "object",
    "required": ["schema_version", "corpus_version", "status", "warnings", "truncated", "data", "error"],
    "properties": {
        "schema_version": {"type": "string"}, "package_version": {"type": "string"},
        "corpus_version": {"type": "string"}, "request_id": {"type": "string"},
        "status": {"type": "string", "enum": ["ok", "no_match", "needs_context", "conflicting_evidence",
                                              "unsupported_profile", "invalid_input", "version_mismatch",
                                              "resource_unavailable", "limit_exceeded"]},
        "warnings": {"type": "array"}, "truncated": {"type": "boolean"},
        "data": {}, "error": {},
    },
}
_SEARCH_SCHEMA = {"type": "object", "required": ["query"],
                  "properties": {"query": {"type": "string", "description": "Persian or English words about a writing question"}}}
_FETCH_SCHEMA = {"type": "object", "required": ["id"],
                 "properties": {"id": {"type": "string", "description": "A rule id from search, such as STY-019"}}}
INSTRUCTIONS = ("Persian writing rules and deterministic text checks for Iranian standard Persian. "
                "Find rules with search_rules (or search) and read them with get_rule (or fetch); when editing a text, "
                "use check_mechanics and validate_patches. Rules are drafts not yet reviewed by a human editor.")


def tool_definitions(chatgpt: bool = False) -> list[types.Tool]:
    tools = [
        types.Tool(name=name, description=desc, input_schema=model.model_json_schema(),
                   output_schema=_ENVELOPE_SCHEMA, annotations=_ANNOTATIONS)
        for name, (model, _fn, desc) in api.TOOLS.items()
    ]
    if chatgpt:
        tools += [
            types.Tool(name="search", input_schema=_SEARCH_SCHEMA, annotations=_ANNOTATIONS,
                       description="Search the Persian writing rules. Returns rule ids, titles and links; read one with fetch."),
            types.Tool(name="fetch", input_schema=_FETCH_SCHEMA, annotations=_ANNOTATIONS,
                       description="Get the full text of one Persian writing rule by id (from search)."),
        ]
    return tools


def _rule_url(rule: dict[str, Any]) -> str:
    return f"{REPO_URL}/blob/main/skills/negaresh/references/rules-{rule['category']}.md"


def _rule_text(rule: dict[str, Any]) -> str:
    lines = [f"{rule['id']} {rule['title_fa']} ({rule['title_en']})",
             f"severity: {rule['severity']}; profiles: {', '.join(rule['profiles'])}", "", rule["guidance"]]
    for ex in rule.get("examples", []):
        note = f" ({ex['note']})" if ex.get("note") else ""
        if "wrong" in ex:
            lines.append(f"- {ex['wrong']} ← {ex.get('right', '')}{note}")
        else:
            lines.append(f"- {ex.get('right') or ex.get('ok', '')}{note}")
    for exc in rule.get("exceptions") or []:
        lines.append(f"* {exc}")
    return "\n".join(lines)


def _text_result(obj: Any, is_error: bool = False) -> types.CallToolResult:
    return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps(obj, ensure_ascii=False))],
                                is_error=is_error)


def _chatgpt_call(name: str, args: dict[str, Any]) -> types.CallToolResult:
    if name == "search":
        env, _ = api.call("search_rules", {"query": str(args.get("query", "")), "limit": 8})
        rules = (env.get("data") or {}).get("results") or []
        return _text_result({"results": [{"id": r["id"], "title": f"{r['id']} {r['title_fa']} / {r['title_en']}",
                                          "url": _rule_url(r)} for r in rules]})
    env, err = api.call("get_rule", {"rule_id": str(args.get("id", ""))})
    rule = None if err else (env.get("data") or {}).get("rule")
    if not rule:
        return _text_result(env, is_error=True)
    return _text_result({"id": rule["id"], "title": f"{rule['id']} {rule['title_fa']}", "text": _rule_text(rule),
                         "url": _rule_url(rule), "metadata": {"category": rule["category"], "severity": rule["severity"]}})


def build_server(chatgpt: bool = False) -> Server:
    async def list_tools(ctx: ServerRequestContext, params: types.PaginatedRequestParams | None) -> types.ListToolsResult:
        return types.ListToolsResult(tools=tool_definitions(chatgpt))

    async def call_tool(ctx: ServerRequestContext, params: types.CallToolRequestParams) -> types.CallToolResult:
        if chatgpt and params.name in ("search", "fetch"):
            return _chatgpt_call(params.name, params.arguments or {})
        env, is_error = api.call(params.name, params.arguments)
        text = json.dumps(env, ensure_ascii=False, separators=(",", ":"))
        return types.CallToolResult(content=[types.TextContent(type="text", text=text)], structured_content=env,
                                    is_error=is_error)

    hint = CacheHint(ttl_ms=0, scope="public")
    return Server(SERVER_NAME, version=__version__, instructions=INSTRUCTIONS,
                  on_list_tools=list_tools, on_call_tool=call_tool,
                  cache_hints={"server/discover": hint, "tools/list": hint})


async def serve() -> None:
    server = build_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


class _McpEndpoint:
    """ASGI app for the /mcp path (a class instance, so Starlette passes scope, receive and send through)."""

    def __init__(self, manager: Any) -> None:
        self.manager = manager

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        await self.manager.handle_request(scope, receive, send)


def http_app(allowed_hosts: list[str] | None = None, allow_any_host: bool = False) -> Any:
    """Starlette app: /mcp (Streamable HTTP, stateless, JSON responses) and GET /health."""
    import contextlib

    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
    from mcp.server.transport_security import TransportSecuritySettings
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    extra = allowed_hosts or []
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=not allow_any_host,
        allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*", *extra],
        allowed_origins=["http://127.0.0.1:*", "http://localhost:*", "https://chatgpt.com", "https://chat.openai.com",
                         "https://claude.ai", *[f"https://{h}" for h in extra]],
    )
    manager = StreamableHTTPSessionManager(build_server(chatgpt=True), stateless=True, json_response=True,
                                           security_settings=security)

    @contextlib.asynccontextmanager
    async def lifespan(app: Any) -> Any:
        async with manager.run():
            yield

    async def health(request: Any) -> JSONResponse:
        return JSONResponse({"status": "ok", "server": SERVER_NAME, "version": __version__})

    return Starlette(routes=[Route("/health", health),
                             Route("/mcp", _McpEndpoint(manager), methods=["GET", "POST", "DELETE"])],
                     lifespan=lifespan)


async def serve_http(host: str = "127.0.0.1", port: int = 8000, allowed_hosts: list[str] | None = None,
                     allow_any_host: bool = False) -> None:
    import uvicorn

    config = uvicorn.Config(http_app(allowed_hosts, allow_any_host), host=host, port=port, log_level="info")
    await uvicorn.Server(config).serve()
