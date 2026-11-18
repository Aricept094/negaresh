"""Command line: serve (MCP over stdio), doctor, corpus-info, and two helpers
for use without an MCP host (check, search)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from importlib import metadata

from . import SCHEMA_VERSION, __version__


def _out(obj: object) -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    json.dump(obj, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def _doctor() -> dict[str, object]:
    from .corpus import load
    info: dict[str, object] = {"package": __version__, "schema": SCHEMA_VERSION, "python": sys.version.split()[0]}
    try:
        info["mcp_sdk"] = metadata.version("mcp")
    except metadata.PackageNotFoundError:
        info["mcp_sdk"] = None
    try:
        corpus = load()
        info.update(corpus_version=corpus.version, rules=len(corpus.rules), profiles=len(corpus.profiles),
                    variant_spellings=len(corpus.lexicon.get("variant_spellings", {})), search_backend="in_memory_scan",
                    healthy=True)
    except Exception as exc:
        info.update(healthy=False, problem=type(exc).__name__)
    return info


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="negaresh")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_serve = sub.add_parser("serve", help="run the MCP server (stdio by default; --http for Streamable HTTP)")
    p_serve.add_argument("--http", action="store_true", help="serve Streamable HTTP at /mcp instead of stdio")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.add_argument("--allowed-host", action="append", default=[],
                         help="extra Host header to accept, such as a tunnel's domain (repeatable)")
    p_serve.add_argument("--allow-any-host", action="store_true",
                         help="turn off Host header checks (only behind a proxy you control)")
    sub.add_parser("doctor", help="print health and version metadata as JSON")
    sub.add_parser("corpus-info", help="print corpus metadata as JSON")
    p_check = sub.add_parser("check", help="run mechanical checks on a UTF-8 text file")
    p_check.add_argument("file")
    p_check.add_argument("--profile")
    p_search = sub.add_parser("search", help="search the rules")
    p_search.add_argument("query")
    args = parser.parse_args(argv)

    if args.cmd == "serve":
        if args.http:
            from .server import serve_http
            asyncio.run(serve_http(args.host, args.port, args.allowed_host, args.allow_any_host))
        else:
            from .server import serve
            asyncio.run(serve())
        return 0
    if args.cmd == "doctor":
        info = _doctor()
        _out(info)
        return 0 if info.get("healthy") else 1
    from . import api
    if args.cmd == "corpus-info":
        _out(api.call("get_profile", {})[0]["data"])
    elif args.cmd == "check":
        try:
            with open(args.file, encoding="utf-8") as fh:
                text = fh.read()
        except UnicodeDecodeError:
            print(f"negaresh: {args.file} is not UTF-8 text", file=sys.stderr)
            return 2
        except OSError as exc:
            print(f"negaresh: cannot read {args.file}: {exc.strerror}", file=sys.stderr)
            return 2
        ctx = {"context": {"profile_id": args.profile}} if args.profile else {}
        env, is_error = api.call("check_mechanics", {"text": text, **ctx})
        _out(env)
        return 1 if is_error else 0
    elif args.cmd == "search":
        env, is_error = api.call("search_rules", {"query": args.query})
        _out(env)
        return 1 if is_error else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
