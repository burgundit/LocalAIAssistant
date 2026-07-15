#!/usr/bin/env python3
"""Create a compact, local-model-generated context pack for coding agents."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


TEXT_EXTENSIONS = {
    ".cs", ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".swift",
    ".go", ".rs", ".cpp", ".cc", ".c", ".h", ".hpp", ".rb", ".php",
    ".ps1", ".sh", ".sql", ".html", ".css", ".scss", ".json", ".toml",
    ".yaml", ".yml", ".xml", ".md", ".txt", ".ini", ".cfg", ".gradle",
}
SPECIAL_FILENAMES = {"dockerfile", "makefile", "gemfile", "procfile"}
SENSITIVE_FILENAMES = {
    ".env", ".env.local", ".env.development", ".env.production", "credentials",
    "credentials.json", "secrets.json", "settings.local.json", "id_rsa", "id_ed25519",
}
IGNORED_DIRS = {
    ".git", ".idea", ".vs", ".vscode", ".local-ai", "node_modules", "vendor",
    "dist", "build", "bin", "obj", "target", "coverage", "library", "logs",
    "temp", "tmp", "packages", "__pycache__", ".pytest_cache", ".venv", "venv",
}
STOP_WORDS = {
    "the", "and", "for", "with", "from", "this", "that", "into", "find", "please",
    "관련", "파일", "파일을", "코드", "찾아", "요약", "요약해줘", "분석", "해줘", "대한", "어떻게", "있는",
}
DEFAULTS = {
    "model": "qwen2.5-coder:7b",
    "output": ".local-ai/context-pack.md",
    "max_files": 16,
    "max_chars": 80_000,
    "max_chars_per_file": 20_000,
    "max_file_bytes": 300_000,
}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


@dataclass
class Candidate:
    path: Path
    relative: str
    text: str
    score: int


def estimate_tokens(text: str) -> int:
    """Estimate tokens cheaply; this is for before/after comparison, not billing."""
    ascii_count = sum(1 for char in text if ord(char) < 128)
    non_ascii_count = len(text) - ascii_count
    return max(1, round(ascii_count / 4 + non_ascii_count / 1.5))


def query_terms(question: str) -> list[str]:
    """Turn a natural-language question into searchable words and remove filler words."""
    terms = re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}|[가-힣]{2,}", question.lower())
    return list(dict.fromkeys(term for term in terms if term not in STOP_WORDS))


def is_text_file(path: Path) -> bool:
    """Allow source-like text while keeping credentials, keys, and local secrets out."""
    name = path.name.lower()
    if name in SENSITIVE_FILENAMES or name.endswith((".pem", ".key", ".pfx", ".p12")):
        return False
    return path.suffix.lower() in TEXT_EXTENSIONS or name in SPECIAL_FILENAMES


def read_text(path: Path, max_file_bytes: int) -> str | None:
    try:
        if path.stat().st_size > max_file_bytes:
            return None
        raw = path.read_bytes()
        if b"\x00" in raw:
            return None
        return raw.decode("utf-8", errors="replace")
    except (OSError, UnicodeError):
        return None


def score_file(relative: str, text: str, terms: list[str]) -> int:
    """Rank filename/path matches above ordinary content matches."""
    if not terms:
        return 1
    path_lower = relative.lower()
    sample = text[:120_000].lower()
    score = 0
    for term in terms:
        if term in Path(relative).name.lower():
            score += 18
        elif term in path_lower:
            score += 9
        occurrences = sample.count(term)
        score += min(occurrences, 12) * 2
    if Path(relative).name.lower() in {"readme.md", "agents.md", "package.json", "pyproject.toml"}:
        score += 2
    return score


def candidate_category(item: Candidate) -> str:
    relative = item.relative.lower()
    name = item.path.name.lower()
    if "test" in name or any(part in {"test", "tests", "spec", "specs"} for part in Path(relative).parts):
        return "tests"
    if item.path.suffix.lower() in {
        ".cs", ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".swift",
        ".go", ".rs", ".cpp", ".cc", ".c", ".h", ".hpp", ".rb", ".php", ".sql",
    }:
        return "code"
    if item.path.suffix.lower() == ".md":
        return "docs"
    return "config"


def select_candidates(
    root: Path,
    question: str,
    max_files: int,
    max_chars: int,
    max_chars_per_file: int,
    max_file_bytes: int,
) -> tuple[list[Candidate], int, int]:
    """Scan once, rank matches, then reserve room for code, tests, docs, and config.

    The per-file limit prevents one large README or design document from consuming
    the entire prompt budget before implementation files can be included.
    """
    terms = query_terms(question)
    candidates: list[Candidate] = []
    scanned_tokens = 0
    scanned_files = 0

    for current_root, dirs, files in os.walk(root):
        dirs[:] = [directory for directory in dirs if directory.lower() not in IGNORED_DIRS]
        base = Path(current_root)
        for filename in files:
            path = base / filename
            if not is_text_file(path):
                continue
            text = read_text(path, max_file_bytes)
            if text is None:
                continue
            relative = path.relative_to(root).as_posix()
            scanned_files += 1
            scanned_tokens += estimate_tokens(text)
            score = score_file(relative, text, terms)
            if score > 0:
                candidates.append(Candidate(path, relative, text, score))

    candidates.sort(key=lambda item: (-item.score, len(item.relative), item.relative.lower()))
    # Seed each category with its best match so a useful answer has both context
    # and implementation evidence when the repository contains those categories.
    diversified: list[Candidate] = []
    for category in ("code", "tests", "docs", "config"):
        first = next((item for item in candidates if candidate_category(item) == category), None)
        if first is not None:
            diversified.append(first)
    diversified.extend(item for item in candidates if item not in diversified)
    selected: list[Candidate] = []
    used_chars = 0
    for item in diversified:
        if len(selected) >= max_files:
            break
        remaining = max_chars - used_chars
        if remaining <= 0:
            break
        excerpt = item.text[: min(remaining, max_chars_per_file)]
        if not excerpt:
            continue
        selected.append(Candidate(item.path, item.relative, excerpt, item.score))
        used_chars += len(excerpt)
    return selected, scanned_files, scanned_tokens


def ollama_request(endpoint: str, payload: dict, timeout: int = 600) -> dict:
    """Call Ollama's local HTTP API; no cloud API key or external upload is used."""
    request = urllib.request.Request(
        f"http://127.0.0.1:11434{endpoint}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def ollama_tags(timeout: int = 5) -> dict:
    with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def build_source_context(selected: list[Candidate]) -> str:
    chunks = []
    for item in selected:
        chunks.append(f"\n--- FILE: {item.relative} | relevance={item.score} ---\n{item.text}")
    return "".join(chunks)


def deterministic_pack(question: str, selected: list[Candidate]) -> str:
    """Create a no-model fallback so file discovery still works offline."""
    lines = [
        "# Local AI Context Pack",
        "",
        "## Task",
        "",
        question,
        "",
        "## Selected files",
        "",
    ]
    for item in selected:
        preview = "\n".join(item.text.splitlines()[:40])
        lines.extend([
            f"### `{item.relative}` (relevance {item.score})",
            "",
            "```text",
            preview,
            "```",
            "",
        ])
    lines.extend([
        "## Handoff instruction",
        "",
        "Verify these excerpts against the repository before editing. Do not assume omitted files are irrelevant.",
    ])
    return "\n".join(lines)


def model_pack(question: str, selected: list[Candidate], model: str) -> str:
    """Ask the local model for a short, evidence-based handoff summary."""
    source_context = build_source_context(selected)
    prompt = f"""You compress repository evidence for a senior coding agent.

User task:
{question}

Repository excerpts:
{source_context}

Produce a compact Markdown context pack in Korean. Preserve exact file paths, symbol names, configuration keys, error messages, and important values. Include only evidence supported by the excerpts. Use these sections:
1. 작업 요약
2. 관련 파일과 역할
3. 확인된 실행 흐름 또는 데이터 흐름
4. 위험과 불확실성
5. Codex/Claude가 확인하거나 실행할 항목

Never claim that you ran tests or commands. Never instruct the agent to trust the summary without checking source files. Do not reproduce long source blocks."""
    result = ollama_request(
        "/api/generate",
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 700},
        },
    )
    return result["response"].strip()


def resolve_output(root: Path, output: str) -> Path:
    path = Path(output).expanduser()
    return path if path.is_absolute() else root / path


def load_config(root: Path) -> dict:
    # Configuration belongs to the target project, so each project can tune its
    # own limits without changing this tool or the user's global environment.
    path = root / ".localassistant.json"
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"설정 파일을 읽을 수 없습니다: {path} ({error})") from error
    if not isinstance(value, dict):
        raise ValueError(f"설정 파일 최상위 값은 객체여야 합니다: {path}")
    return value


def setting(args: argparse.Namespace, config: dict, name: str):
    argument_value = getattr(args, name, None)
    return argument_value if argument_value is not None else config.get(name, DEFAULTS[name])


def cache_key(question: str, model: str, selected: list[Candidate]) -> str:
    """Invalidate cached summaries whenever the question, model, or source changes."""
    digest = hashlib.sha256()
    digest.update(b"local-assistant-v3\0")
    digest.update(model.encode("utf-8"))
    digest.update(b"\0")
    digest.update(question.encode("utf-8"))
    for item in selected:
        digest.update(b"\0")
        digest.update(item.relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(item.text.encode("utf-8"))
    return digest.hexdigest()


def copy_to_clipboard(text: str) -> None:
    """Copy Unicode safely on Windows; this avoids Korean console code-page issues."""
    if os.name == "nt":
        # CF_UNICODETEXT through Win32 avoids console code-page corruption.
        cf_unicode_text = 13
        gmem_moveable = 0x0002
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32
        kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
        kernel32.GlobalAlloc.restype = ctypes.c_void_p
        kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
        user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
        user32.SetClipboardData.restype = ctypes.c_void_p
        encoded = (text + "\0").encode("utf-16-le")
        handle = kernel32.GlobalAlloc(gmem_moveable, len(encoded))
        if not handle:
            raise OSError("클립보드 메모리를 할당하지 못했습니다.")
        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            kernel32.GlobalFree(handle)
            raise OSError("클립보드 메모리를 잠글 수 없습니다.")
        ctypes.memmove(pointer, encoded, len(encoded))
        kernel32.GlobalUnlock(handle)
        if not user32.OpenClipboard(None):
            kernel32.GlobalFree(handle)
            raise OSError("클립보드를 열 수 없습니다.")
        try:
            user32.EmptyClipboard()
            if not user32.SetClipboardData(cf_unicode_text, handle):
                raise OSError("클립보드에 쓸 수 없습니다.")
            handle = None  # Ownership transfers to the system.
        finally:
            user32.CloseClipboard()
            if handle:
                kernel32.GlobalFree(handle)
        return
    command = shutil.which("pbcopy") or shutil.which("xclip")
    if not command:
        raise OSError("지원되는 클립보드 명령을 찾지 못했습니다.")
    subprocess.run([command], input=text.encode("utf-8"), check=True)


def command_doctor(args: argparse.Namespace) -> int:
    executable = shutil.which("ollama")
    if not executable and os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        candidate = Path(local_app_data) / "Programs" / "Ollama" / "ollama.exe" if local_app_data else None
        if candidate and candidate.is_file():
            executable = str(candidate)
    print(f"Python: {sys.version.split()[0]}")
    print(f"Ollama PATH: {executable or '찾을 수 없음 (새 터미널을 열어보세요)'}")
    try:
        tags = ollama_tags()
    except (OSError, urllib.error.URLError) as error:
        print(f"Ollama API: 연결 실패 ({error})")
        return 1
    models = [item.get("name", "") for item in tags.get("models", [])]
    print("Ollama API: 정상")
    print(f"설치된 모델: {', '.join(models) if models else '없음'}")
    print(f"선택 모델 {args.model}: {'준비됨' if args.model in models else '설치 필요'}")
    return 0


def command_pack(args: argparse.Namespace) -> int:
    root = Path(args.path).expanduser().resolve()
    if not root.is_dir():
        print(f"프로젝트 경로를 찾을 수 없습니다: {root}", file=sys.stderr)
        return 2

    try:
        config = load_config(root)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2
    model = setting(args, config, "model")
    output = setting(args, config, "output")
    max_files = int(setting(args, config, "max_files"))
    max_chars = int(setting(args, config, "max_chars"))
    max_chars_per_file = int(setting(args, config, "max_chars_per_file"))
    max_file_bytes = int(setting(args, config, "max_file_bytes"))
    if min(max_files, max_chars, max_chars_per_file, max_file_bytes) <= 0:
        print("파일 및 크기 제한은 0보다 커야 합니다.", file=sys.stderr)
        return 2

    selected, scanned_files, scanned_tokens = select_candidates(
        root, args.question, max_files, max_chars, max_chars_per_file, max_file_bytes
    )
    if not selected:
        print("질문과 관련된 텍스트 파일을 찾지 못했습니다.", file=sys.stderr)
        return 3

    source_context = build_source_context(selected)
    used_model = not args.no_model
    output_path = resolve_output(root, output)
    key = cache_key(args.question, model, selected)
    cache_path = output_path.parent / "cache" / f"{key}.md"
    cache_hit = used_model and not args.no_cache and cache_path.is_file()
    try:
        if cache_hit:
            content = cache_path.read_text(encoding="utf-8")
        elif used_model:
            content = model_pack(args.question, selected, model)
            if not args.no_cache:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(content, encoding="utf-8")
        else:
            content = deterministic_pack(args.question, selected)
    except (OSError, KeyError, urllib.error.URLError, json.JSONDecodeError) as error:
        print(f"Ollama 호출 실패: {error}", file=sys.stderr)
        print("--no-model 옵션으로 파일 선별만 실행할 수 있습니다.", file=sys.stderr)
        return 4


    input_tokens = estimate_tokens(source_context)
    output_tokens = estimate_tokens(content)
    saving = max(0.0, (1 - output_tokens / input_tokens) * 100) if input_tokens else 0.0
    evidence_index = "\n".join(f"- `{item.relative}` (relevance {item.score})" for item in selected)
    metadata = (
        "\n\n---\n"
        "## Evidence index\n\n"
        f"{evidence_index}\n\n"
        "## Context pack metrics\n\n"
        f"- Root: `{root}`\n"
        f"- Scanned: {scanned_files} files / ~{scanned_tokens:,} estimated tokens\n"
        f"- Selected: {len(selected)} files / ~{input_tokens:,} estimated tokens\n"
        f"- Pack: ~{output_tokens:,} estimated tokens\n"
        f"- Local compression saving: ~{saving:.1f}%\n"
        f"- Model: `{model if used_model else 'none (deterministic excerpts)'}`\n"
        f"- Cache: `{'hit' if cache_hit else 'miss' if used_model and not args.no_cache else 'disabled'}`\n"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_content = content + metadata
    output_path.write_text(final_content, encoding="utf-8")

    if args.copy:
        try:
            copy_to_clipboard(final_content)
        except OSError as error:
            print(f"컨텍스트 팩은 생성했지만 클립보드 복사에 실패했습니다: {error}", file=sys.stderr)
            return 5

    print(f"컨텍스트 팩 생성: {output_path}")
    print(f"선별 입력: ~{input_tokens:,} tokens → 결과: ~{output_tokens:,} tokens ({saving:.1f}% 절감)")
    if args.copy:
        print("컨텍스트 팩을 클립보드에 복사했습니다.")
    if cache_hit:
        print("동일한 입력의 로컬 모델 캐시를 재사용했습니다.")
    print("선택 파일:")
    for item in selected:
        print(f"  {item.score:>3}  {item.relative}")
    return 0


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local context compressor for Codex and Claude Code")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Ollama 연결과 모델 설치 상태 확인")
    doctor.add_argument("--model", default="qwen2.5-coder:7b")
    doctor.set_defaults(func=command_doctor)

    pack = subparsers.add_parser("pack", help="질문에 맞는 작은 컨텍스트 팩 생성")
    pack.add_argument("--question", required=True)
    pack.add_argument("--path", default=".")
    pack.add_argument("--model")
    pack.add_argument("--output")
    pack.add_argument("--no-model", action="store_true")
    pack.add_argument("--no-cache", action="store_true")
    pack.add_argument("--copy", action="store_true")
    pack.add_argument("--max-files", type=int)
    pack.add_argument("--max-chars", type=int)
    pack.add_argument("--max-chars-per-file", type=int)
    pack.add_argument("--max-file-bytes", type=int)
    pack.set_defaults(func=command_pack)
    return parser


def main() -> int:
    args = make_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
