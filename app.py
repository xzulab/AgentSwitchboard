#!/usr/bin/env python3
"""Agent Switchboard - Python backend (lightweight Flask app).

Usage:
    python app.py --port 5173
    python app.py
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, abort, send_from_directory

ROOT = Path(__file__).resolve().parent
TEMPLATE_DIR = ROOT / "templates"
STATIC_DIR = ROOT / "static"
BACKUP_DIR = ROOT / ".backups"

ALLOWED_PATHS: list[Path] = []

DEFAULT_TRUSTED = [
    Path.home() / ".claude",
    Path.home() / ".codex",
    Path.home() / ".config" / "opencode",
]

app = Flask(__name__, template_folder=str(TEMPLATE_DIR), static_folder=str(STATIC_DIR))


def _resolve(path_str: str) -> Path | None:
    if not path_str:
        return None
    p = Path(path_str).expanduser()
    if not p.is_absolute():
        return None
    try:
        p.resolve(strict=False)
    except Exception:
        return None
    return p


def _is_allowed(p: Path) -> bool:
    resolved = p.resolve()
    for allowed in ALLOWED_PATHS:
        try:
            resolved.relative_to(allowed)
            return True
        except ValueError:
            continue
    return False


def _ensure_allowed(p: Path) -> Path:
    resolved = p.resolve()
    if not _is_allowed(resolved):
        abort(403, f"Path not allowed: {p}")
    return resolved


FILE_DEFS = {
    "claude": {
        "label": "Claude Settings",
        "file": "settings.json",
        "path": "~/.claude/settings.json",
    },
    "codexConfig": {
        "label": "Codex Config",
        "file": "config.toml",
        "path": "~/.codex/config.toml",
    },
    "codexAuth": {
        "label": "Codex Auth",
        "file": "auth.json",
        "path": "~/.codex/auth.json",
    },
    "opencode": {
        "label": "OpenCode JSON",
        "file": "opencode.json",
        "path": "~/.config/opencode/opencode.json",
    },
}


@app.before_request
def _check_traversal():
    for key in ("path", "dir"):
        val = request.args.get(key, "")
        if ".." in val.split("/"):
            abort(400, "Invalid path")


@app.route("/")
def index():
    return send_from_directory(str(TEMPLATE_DIR), "index.html")


@app.route("/api/file/read", methods=["GET"])
def api_file_read():
    path_str = request.args.get("path", "").strip()
    p = _resolve(path_str)
    if p is None or not p.is_file():
        abort(404, f"File not found: {path_str}")
    p = _ensure_allowed(p)
    try:
        data = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        data = p.read_bytes().decode("utf-8", errors="replace")
    return jsonify({"path": str(p), "content": data, "size": len(data)})


@app.route("/api/file/write", methods=["POST"])
def api_file_write():
    body = request.get_json(silent=True) or {}
    path_str = body.get("path", "").strip()
    content = body.get("content", "")
    p = _resolve(path_str)
    if p is None:
        abort(400, "Invalid path")
    p = _ensure_allowed(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return jsonify({"ok": True, "path": str(p), "bytes": len(content.encode())})


@app.route("/api/file/upload", methods=["POST"])
def api_file_upload():
    key = request.form.get("key", "").strip()
    if key not in FILE_DEFS:
        abort(400, "Invalid key")
    if "file" not in request.files:
        abort(400, "No file provided")
    f = request.files["file"]
    if f.filename == "":
        abort(400, "Empty filename")
    defn = FILE_DEFS[key]
    target = Path(defn["path"]).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    target = _ensure_allowed(target)
    raw = f.read()
    target.write_bytes(raw)
    return jsonify({"ok": True, "path": str(target), "bytes": len(raw)})


@app.route("/api/dir/list", methods=["GET"])
def api_dir_list():
    path_str = request.args.get("dir", "").strip()
    hidden = request.args.get("hidden", "1") == "1"
    p = _resolve(path_str)
    if p is None or not p.is_dir():
        abort(404, f"Directory not found: {path_str}")
    p = _ensure_allowed(p)
    items = []
    for entry in sorted(p.iterdir()):
        if not hidden and entry.name.startswith("."):
            continue
        items.append({
            "name": entry.name,
            "path": str(entry),
            "is_dir": entry.is_dir(),
            "is_file": entry.is_file(),
            "size": entry.stat().st_size if entry.is_file() else None,
            "hidden": entry.name.startswith("."),
        })
    return jsonify({"path": str(p), "items": items})


@app.route("/api/config/paths", methods=["GET"])
def api_config_paths():
    return jsonify(FILE_DEFS)


@app.route("/api/backups/create", methods=["POST"])
def api_backups_create():
    body = request.get_json(silent=True) or {}
    paths = body.get("paths", [])
    if not isinstance(paths, list):
        abort(400, "paths must be a list")
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = BACKUP_DIR / ts
    backup_root.mkdir(parents=True, exist_ok=True)
    written = 0
    for p_str in paths:
        p = _resolve(p_str)
        if p and p.is_file() and _is_allowed(p):
            p = _ensure_allowed(p)
            rel = p.parent.name / p.name
            dest = backup_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest)
            written += 1
    return jsonify({"ok": True, "backup_dir": str(backup_root), "files": written})


@app.route("/api/backups/list", methods=["GET"])
def api_backups_list():
    if not BACKUP_DIR.exists():
        return jsonify({"backups": []})
    items = []
    for d in sorted(BACKUP_DIR.iterdir(), reverse=True):
        if d.is_dir():
            count = sum(1 for _ in d.rglob("*"))
            mtime = datetime.fromtimestamp(d.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            items.append({"dir": d.name, "files": count, "created": mtime})
    return jsonify({"backups": items})


@app.route("/api/backups/restore/<name>", methods=["POST"])
def api_backups_restore(name: str):
    backup = BACKUP_DIR / name
    if not backup.is_dir():
        abort(404, "Backup not found")
    restored = 0
    for src in backup.rglob("*"):
        if src.is_file():
            rel = src.relative_to(backup)
            parts = list(rel.parts)
            if len(parts) >= 2:
                home_sub = Path.home() / Path(*parts[1:])
                home_sub.parent.mkdir(parents=True, exist_ok=True)
                home_sub = _ensure_allowed(home_sub)
                shutil.copy2(src, home_sub)
                restored += 1
    return jsonify({"ok": True, "restored": restored})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agent Switchboard")
    parser.add_argument("--port", type=int, default=5173)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--trust-dir", action="append", default=[])
    args = parser.parse_args()

    import __main__ as _m
    _m.ALLOWED_PATHS = [
        *DEFAULT_TRUSTED,
        *(Path(d).expanduser() for d in args.trust_dir),
    ]
    _m.ALLOWED_PATHS = [p.resolve(strict=False) for p in _m.ALLOWED_PATHS if p]

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n  Agent Switchboard")
    print(f"  -> http://{args.host}:{args.port}/")
    print(f"  Trust roots: {[str(p) for p in _m.ALLOWED_PATHS]}")
    print()

    app.run(host=args.host, port=args.port, debug=args.debug, use_reloader=False)
