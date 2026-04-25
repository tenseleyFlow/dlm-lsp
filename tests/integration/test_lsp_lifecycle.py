"""Integration test: full LSP lifecycle over stdio subprocess."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any


def _encode_lsp_message(obj: dict[str, Any]) -> bytes:
    body = json.dumps(obj).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    return header + body


def _read_lsp_response(proc: subprocess.Popen[bytes]) -> dict[str, Any]:
    assert proc.stdout is not None
    content_length = 0
    while True:
        line = proc.stdout.readline()
        if not line:
            return {}
        decoded = line.decode("ascii")
        if decoded.strip() == "":
            break
        if decoded.lower().startswith("content-length:"):
            content_length = int(decoded.split(":", 1)[1].strip())

    if content_length == 0:
        return {}
    body = proc.stdout.read(content_length)
    return json.loads(body)


def test_initialize_and_shutdown() -> None:
    proc = subprocess.Popen(
        [sys.executable, "-m", "dlm_lsp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdin is not None

    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "processId": None,
            "rootUri": None,
            "capabilities": {},
        },
    }
    proc.stdin.write(_encode_lsp_message(init_request))
    proc.stdin.flush()

    response = _read_lsp_response(proc)
    assert response.get("id") == 1
    result = response.get("result", {})
    capabilities = result.get("capabilities", {})
    assert "completionProvider" in capabilities
    assert "hoverProvider" in capabilities

    initialized_notif = {
        "jsonrpc": "2.0",
        "method": "initialized",
        "params": {},
    }
    proc.stdin.write(_encode_lsp_message(initialized_notif))
    proc.stdin.flush()

    shutdown_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "shutdown",
        "params": None,
    }
    proc.stdin.write(_encode_lsp_message(shutdown_request))
    proc.stdin.flush()

    shutdown_resp = _read_lsp_response(proc)
    assert shutdown_resp.get("id") == 2

    exit_notif = {
        "jsonrpc": "2.0",
        "method": "exit",
        "params": None,
    }
    proc.stdin.write(_encode_lsp_message(exit_notif))
    proc.stdin.flush()

    proc.wait(timeout=5)
    assert proc.returncode == 0


def test_open_document_and_get_completions() -> None:
    proc = subprocess.Popen(
        [sys.executable, "-m", "dlm_lsp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdin is not None

    _send(
        proc,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "processId": None,
                "rootUri": None,
                "capabilities": {},
            },
        },
    )
    _read_lsp_response(proc)

    _send(proc, {"jsonrpc": "2.0", "method": "initialized", "params": {}})

    dlm_text = (
        "---\n"
        "dlm_id: 01KPQ9M3000000000000000000\n"
        "dlm_version: 15\n"
        "base_model: smollm2-135m\n"
        "---\n"
        "Some prose.\n"
        "\n"
    )
    _send(
        proc,
        {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": "file:///test.dlm",
                    "languageId": "dlm",
                    "version": 1,
                    "text": dlm_text,
                }
            },
        },
    )

    # Send completion request; drain interleaved notifications until we
    # find the response with id=10.
    _send(
        proc,
        {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "textDocument/completion",
            "params": {
                "textDocument": {"uri": "file:///test.dlm"},
                "position": {"line": 3, "character": 13},
            },
        },
    )

    comp_resp: dict[str, Any] = {}
    for _ in range(10):
        msg = _read_lsp_response(proc)
        if msg.get("id") == 10:
            comp_resp = msg
            break
    assert comp_resp.get("id") == 10
    items = comp_resp.get("result", {}).get("items", [])
    labels = {item["label"] for item in items}
    assert "smollm2-135m" in labels

    _send(proc, {"jsonrpc": "2.0", "id": 99, "method": "shutdown", "params": None})
    _read_lsp_response(proc)
    _send(proc, {"jsonrpc": "2.0", "method": "exit", "params": None})
    proc.wait(timeout=5)


def _send(proc: subprocess.Popen[bytes], msg: dict[str, Any]) -> None:
    assert proc.stdin is not None
    proc.stdin.write(_encode_lsp_message(msg))
    proc.stdin.flush()
