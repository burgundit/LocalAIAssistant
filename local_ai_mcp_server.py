#!/usr/bin/env python3
"""Lumi MCP server that exposes the local Ollama helpers to Claude Code.

Register this as a project MCP server (see .mcp.json) so Claude Code can call
the local model directly for simple, self-contained work instead of spending
its own context and cloud usage on it. Repository-wide scanning and first-pass
summarizing then happen on the local machine via local_ai_pack.
"""

from __future__ import annotations

import urllib.error
from pathlib import Path

from mcp.server.fastmcp import FastMCP

import local_assistant as la

mcp = FastMCP("lumi")


@mcp.tool()
def local_ai_doctor(model: str = la.DEFAULTS["model"]) -> str:
    """Lumi: check whether Ollama is reachable and whether `model` is installed.

    Call this if a local_ai_ask or local_ai_pack call fails, to see whether
    Ollama needs to be started (`ollama serve`) or the model needs to be
    pulled (`ollama pull <model>`).
    """
    try:
        tags = la.ollama_tags()
    except (OSError, urllib.error.URLError) as error:
        return f"Ollama API: 연결 실패 ({error}). 'ollama serve'가 실행 중인지 확인하세요."
    models = [item.get("name", "") for item in tags.get("models", [])]
    lines = [
        "Ollama API: 정상",
        f"설치된 모델: {', '.join(models) if models else '없음'}",
        f"선택 모델 {model}: {'준비됨' if model in models else f'설치 필요 (ollama pull {model})'}",
    ]
    return "\n".join(lines)


@mcp.tool()
def local_ai_ask(question: str, model: str = la.DEFAULTS["model"]) -> str:
    """Lumi: answer a short, self-contained question with local Ollama.

    Use this for simple work that does not need the current repository's
    files: quick explanations, syntax/API questions, wording or format
    conversions, or other lookups a small local model can answer on its own.
    This keeps trivial work off Claude Code's own context and cloud usage.
    Do NOT use it for questions that depend on this project's actual code -
    use local_ai_pack for those instead.
    """
    try:
        result = la.ollama_request(
            "/api/generate",
            {
                "model": model,
                "prompt": question,
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 500},
            },
        )
    except (OSError, urllib.error.URLError) as error:
        return f"로컬 Ollama 호출 실패: {error}. local_ai_doctor로 상태를 확인하세요."
    return result["response"].strip()


@mcp.tool()
def local_ai_pack(
    question: str,
    path: str = ".",
    model: str | None = None,
    max_files: int | None = None,
    max_chars: int | None = None,
    no_model: bool = False,
) -> str:
    """Lumi: scan a project locally and return a compact evidence-based pack.

    Ranks the repository's files against `question`, then has the local
    Ollama model (or, if no_model=True, raw excerpts) summarize only the
    relevant code, tests, docs, and config. Use this before answering
    questions that need real repository evidence, so file scanning and
    first-pass summarizing happen on the local machine instead of consuming
    Claude Code's own context budget. The result is a summary for
    orientation - verify referenced paths and excerpts against the actual
    files before editing anything.
    """
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        return f"프로젝트 경로를 찾을 수 없습니다: {root}"

    try:
        config = la.load_config(root)
    except ValueError as error:
        return str(error)

    resolved_model = model or config.get("model", la.DEFAULTS["model"])
    resolved_max_files = int(max_files or config.get("max_files", la.DEFAULTS["max_files"]))
    resolved_max_chars = int(max_chars or config.get("max_chars", la.DEFAULTS["max_chars"]))
    max_chars_per_file = int(config.get("max_chars_per_file", la.DEFAULTS["max_chars_per_file"]))
    max_file_bytes = int(config.get("max_file_bytes", la.DEFAULTS["max_file_bytes"]))
    output = config.get("output", la.DEFAULTS["output"])

    try:
        pack = la.generate_pack(
            root, question, resolved_model, output, resolved_max_files, resolved_max_chars,
            max_chars_per_file, max_file_bytes, no_model, no_cache=False,
        )
    except LookupError as error:
        return str(error)
    except (OSError, KeyError, urllib.error.URLError) as error:
        return f"Ollama 호출 실패: {error}. no_model=True로 파일 선별만 받을 수 있습니다."

    return pack.content


if __name__ == "__main__":
    mcp.run()
