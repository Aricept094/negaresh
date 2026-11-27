"""Command line: serve (MCP over stdio), doctor, corpus-info, and helpers that do
the server's work without a running server (check, validate, search, rule, profile).
Each helper runs once and exits, so a skill can call it only when it needs it."""

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


def _read_text(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8", newline="") as fh:
            return fh.read()
    except UnicodeDecodeError:
        print(f"negaresh: {path} is not UTF-8 text", file=sys.stderr)
    except OSError as exc:
        print(f"negaresh: cannot read {path}: {exc.strerror}", file=sys.stderr)
    return None


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
    p_valid = sub.add_parser("validate", help="validate edits to a UTF-8 text file (the same check as validate_patches)")
    p_valid.add_argument("file", help="the original text, exactly as it was checked")
    p_valid.add_argument("patches", help="JSON file: a list of patches, or an object with 'patches' and "
                                         "optional 'text_revision' and 'protected_spans'")
    p_valid.add_argument("--out", help="write the revised text to this file when validation passes")
    p_search = sub.add_parser("search", help="search the rules")
    p_search.add_argument("query")
    p_search.add_argument("--profile")
    p_rule = sub.add_parser("rule", help="print one rule in full")
    p_rule.add_argument("rule_id")
    p_profile = sub.add_parser("profile", help="print a profile's conventions, or the list of profiles")
    p_profile.add_argument("profile_id", nargs="?")
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
        text = _read_text(args.file)
        if text is None:
            return 2
        ctx = {"context": {"profile_id": args.profile}} if args.profile else {}
        env, is_error = api.call("check_mechanics", {"text": text, **ctx})
        _out(env)
        return 1 if is_error else 0
    elif args.cmd == "validate":
        from .textutil import revision_of
        text = _read_text(args.file)
        raw = _read_text(args.patches)
        if text is None or raw is None:
            return 2
        try:
            spec = json.loads(raw)
        except json.JSONDecodeError as exc:
            print(f"negaresh: {args.patches} is not valid JSON: {exc.msg}", file=sys.stderr)
            return 2
        if isinstance(spec, list):
            spec = {"patches": spec}
        if not isinstance(spec, dict):
            print(f"negaresh: {args.patches} must hold a list of patches or an object with 'patches'", file=sys.stderr)
            return 2
        payload = {"text_revision": revision_of(text), **spec, "original_text": text}
        env, is_error = api.call("validate_patches", payload)
        data = env.get("data") or {}
        valid = not is_error and env.get("status") == "ok" and data.get("valid") is True
        if args.out and valid and isinstance(data.get("revised_text"), str):
            with open(args.out, "w", encoding="utf-8", newline="") as fh:
                fh.write(data["revised_text"])
        _out(env)
        return 0 if valid else 1
    elif args.cmd == "search":
        ctx = {"context": {"profile_id": args.profile}} if args.profile else {}
        env, is_error = api.call("search_rules", {"query": args.query, **ctx})
        _out(env)
        return 1 if is_error else 0
    elif args.cmd == "rule":
        env, is_error = api.call("get_rule", {"rule_id": args.rule_id})
        _out(env)
        return 1 if is_error or env.get("status") != "ok" else 0
    elif args.cmd == "profile":
        env, is_error = api.call("get_profile", {"profile_id": args.profile_id} if args.profile_id else {})
        _out(env)
        return 1 if is_error else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
