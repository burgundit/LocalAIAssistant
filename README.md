# Local AI Assistant for Codex & Claude Code

> 초보자를 위한 무료 로컬 AI 코딩 도우미 — Ollama로 Codex·Claude Code 입력 토큰과 비용을 줄여보세요.

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Ollama](https://img.shields.io/badge/Ollama-local_AI-black)](https://ollama.com/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**LocalAIAssistant**는 전체 코드 저장소를 Codex나 Claude Code에 그대로 보내는 대신, 무료 로컬 AI 모델이 관련 파일을 먼저 찾고 짧게 압축하는 오픈소스 도구입니다. 복잡한 RAG 설정이나 유료 API 키 없이 Windows PowerShell에서 시작할 수 있습니다.

English: A beginner-friendly local AI context compressor for Ollama, Codex, and Claude Code. It selects relevant repository files, summarizes them locally, and creates a compact prompt to reduce cloud AI input tokens.

## 이런 분에게 적합합니다

- Ollama를 처음 설치하고 어디에 활용할지 찾는 분
- Codex 또는 Claude Code의 토큰 사용량과 비용을 줄이고 싶은 분
- 로컬 AI 코딩 도우미를 복잡한 서버 없이 사용하고 싶은 분
- 큰 프로젝트에서 관련 파일만 골라 AI에게 전달하고 싶은 분

전체 파일을 클라우드 AI에 보내지 않으므로 반복적인 코드 탐색과 요약은 내 PC에서 처리됩니다. 최종 수정과 테스트 판단은 Codex 또는 Claude Code에 맡길 수 있습니다.

## 3분 만에 시작하기

### 1. 준비물

- Windows 11
- Python 3.11 이상
- [Ollama for Windows](https://ollama.com/download/windows)

### 2. 무료 코딩 모델 설치

```powershell
ollama pull qwen2.5-coder:7b
```

### 3. 저장소 내려받기 및 실행

```powershell
git clone https://github.com/burgundit/LocalAIAssistant.git
cd LocalAIAssistant

.\Ask-LocalAssistant.ps1 `
  -Question "로그인 오류의 원인과 확인할 테스트를 요약해줘" `
  -Path C:\path\to\your-project `
  -Copy
```

생성된 요약은 `.local-ai\context-pack.md`에 저장되고 클립보드에도 복사됩니다. Codex나 Claude Code 채팅에 붙여 넣으면 됩니다.

처음이라면 `-Question`에는 “무엇을 알고 싶은지”를 자연스럽게 적으면 됩니다. 예를 들어 `로그인 오류의 원인과 관련 테스트를 찾아줘`처럼 작성할 수 있습니다. 도구가 파일을 수정하거나 명령을 실행하지는 않습니다.

## 무엇이 절약되나요?

```text
전체 프로젝트 파일
        ↓ 로컬 검색
관련 코드·테스트·문서만 선택
        ↓ Ollama 로컬 요약
작은 컨텍스트 팩
        ↓
Codex / Claude Code에 전달
```

실제 261개 파일 프로젝트 검증에서는 약 425,047 추정 토큰의 전체 후보를 검색하여 30,925 토큰만 로컬 모델에 전달했고, 최종 클라우드 AI용 팩은 약 425 토큰으로 압축됐습니다. 토큰 수는 문자 기반 추정치이며 실제 서비스 청구량과는 다를 수 있습니다.

## 권장 환경과 모델

- Windows 11
- Python 3.11 이상
- Ollama
- 첫 모델: `qwen2.5-coder:7b`

RTX 5070 12GB에서는 7B 모델이 속도와 품질의 균형이 좋습니다.

## 기본 사용법

새 PowerShell을 열고 다음을 실행합니다.

```powershell
ollama pull qwen2.5-coder:7b
.\Start-LocalAssistant.ps1 -Doctor
.\Ask-LocalAssistant.ps1 -Question "전투 시작 흐름과 관련된 파일을 찾아 요약해줘" -Path C:\path\to\project
```

결과는 기본적으로 현재 폴더의 `.local-ai\context-pack.md`에 저장됩니다. 이 파일의 내용만 Codex 또는 Claude Code에 전달하면 됩니다.

바로 붙여 넣으려면 `-Copy`를 추가합니다.

```powershell
.\Ask-LocalAssistant.ps1 -Question "테스트 실패 원인을 압축해줘" -Path C:\path\to\project -Copy
```

## 동작 방식

1. 질문에서 검색어를 추출합니다.
2. 파일명, 경로, 파일 내용의 검색어 일치도를 계산합니다.
3. 점수가 높은 파일만 제한된 크기로 읽습니다.
4. Ollama가 코드 사실, 관련 심볼, 위험, 확인할 테스트 중심으로 압축합니다.
5. 원본 후보 크기와 최종 컨텍스트 팩의 추정 토큰 수를 비교합니다.

기본 입력 예산은 총 80,000자, 파일당 20,000자로 제한됩니다. 32K 컨텍스트 모델에 프롬프트와 출력 여유를 남기면서 큰 문서 하나가 예산을 독점하지 않게 합니다.

`.env`, 자격 증명 JSON, 로컬 설정, 개인키·인증서 파일은 기본적으로 읽지 않습니다.

### 파일별 역할

- `local_assistant.py`: 파일 검색, 관련도 계산, Ollama 호출, 요약·캐시 생성
- `Ask-LocalAssistant.ps1`: 초보자가 PowerShell에서 질문을 입력하는 실행 래퍼
- `Start-LocalAssistant.ps1`: Python·Ollama 연결과 모델 설치 상태 점검
- `.localassistant.example.json`: 프로젝트별 파일 수·컨텍스트 크기 설정 예시
- `test_local_assistant.py`: 검색, 보안 제외, 캐시 키 등 핵심 동작 테스트

## 명령 예시

```powershell
# 환경 점검
python .\local_assistant.py doctor

# Ollama를 사용해 컨텍스트 팩 생성
python .\local_assistant.py pack --path C:\path\to\project --question "로그인 오류 원인을 찾아줘"

# 모델 없이 파일 선별 결과만 확인
python .\local_assistant.py pack --path . --question "설정 로딩" --no-model

# 출력 위치와 모델 변경
python .\local_assistant.py pack --path . --question "테스트 실패 분석" --model qwen2.5-coder:7b --output .local-ai\test-failure.md
```

같은 질문과 동일한 파일 내용으로 다시 실행하면 로컬 모델 응답 캐시를 사용합니다. 강제로 다시 생성하려면 `-NoCache` 또는 `--no-cache`를 사용합니다.

프로젝트별 제한을 바꾸려면 `.localassistant.example.json`을 대상 프로젝트의 `.localassistant.json`으로 복사한 뒤 값을 조정합니다. 명령행 옵션이 설정 파일보다 우선합니다.

## 토큰 절감의 의미

표시되는 토큰은 문자 수 기반 추정치입니다. 실제 Codex/Claude 토큰 수와 정확히 같지는 않지만, 전체 파일을 전달했을 때와 압축 팩을 전달했을 때의 상대적인 크기를 확인하는 용도입니다.

로컬 모델의 출력은 참고 자료입니다. 파일 수정, Git 작업, 테스트 실행과 최종 판단은 Codex 또는 Claude Code에서 수행하는 것을 권장합니다.
