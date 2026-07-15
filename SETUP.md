# Codex·Claude Code 연동 설치 가이드

이 문서는 Windows 초보자가 **Lumi(루미)**를 설치하고 Codex 또는 Claude Code와 함께 사용하는 순서입니다. GitHub 저장소 이름은 검색을 위해 `LocalAIAssistant`로 유지됩니다.

## 1. 공통 준비

PowerShell을 새로 열고 다음 명령으로 준비 상태를 확인합니다.

```powershell
python --version
node --version
ollama --version
```

필요한 프로그램:

- Python 3.11 이상: [python.org](https://www.python.org/downloads/)
- Node.js 18 이상: [nodejs.org](https://nodejs.org/)
- Ollama for Windows: [ollama.com/download/windows](https://ollama.com/download/windows)

Ollama가 설치되면 코딩 모델을 한 번 내려받습니다.

```powershell
ollama pull qwen2.5-coder:7b
ollama list
```

## 2. LocalAIAssistant 설치

```powershell
git clone https://github.com/burgundit/LocalAIAssistant.git
cd LocalAIAssistant
python local_assistant.py doctor
```

`Ollama API: 정상`과 `qwen2.5-coder:7b: 준비됨`이 나오면 준비가 끝난 것입니다.

## 3. PC 사양에 맞추기

처음에는 아래 표의 모델과 제한값을 그대로 사용하면 됩니다.

| PC | 모델 | 명령에 추가할 값 |
| --- | --- | --- |
| RAM 16GB, GPU 없음 | `qwen2.5-coder:3b` | `--max-files 6 --max-chars 30000` |
| VRAM 6–8GB | `qwen2.5-coder:7b` | `--max-files 10 --max-chars 50000` |
| VRAM 10–12GB, RAM 32GB | `qwen2.5-coder:7b` | 기본값 |
| VRAM 16GB 이상, RAM 32GB 이상 | `qwen2.5-coder:14b` | 모델별 컨텍스트 한도 확인 |

CPU 전용 PC는 첫 응답이 느릴 수 있습니다. 먼저 `--no-model`로 파일 선택이 맞는지 확인한 다음, 질문과 파일 수를 줄여 실행하세요. 14B 모델이 느리거나 메모리를 많이 사용하면 7B 모델로 내리면 됩니다.

## 4. 권장 방식: Codex·Claude Code에 요약 팩 붙여 넣기

이 방식은 Codex와 Claude Code의 원래 기능·로그인·도구를 유지하면서, 반복적인 저장소 탐색 컨텍스트만 줄입니다.

### Codex CLI 설치

Codex CLI 공식 안내에 따라 설치하고 로그인합니다.

```powershell
npm install -g @openai/codex
codex login
```

프로젝트에서 Codex를 시작합니다.

```powershell
cd C:\path\to\your-project
codex
```

다른 PowerShell 창에서 요약 팩을 만들고 클립보드에 복사합니다.

```powershell
python C:\path\to\LocalAIAssistant\local_assistant.py pack `
  --path C:\path\to\your-project `
  --question "로그인 오류의 원인, 관련 파일, 확인할 테스트를 찾아줘" `
  --copy
```

Codex 채팅에 `Ctrl+V`로 붙여 넣고 다음처럼 요청합니다.

```text
위 컨텍스트 팩은 탐색용 요약이다. 원본 파일을 직접 다시 확인한 뒤
원인을 설명하고, 수정안과 실행할 테스트를 제안해줘.
```

### Claude Code 설치

Anthropic 공식 안내에 따라 설치합니다.

```powershell
npm install -g @anthropic-ai/claude-code
claude doctor
```

Windows에서는 Claude Code가 Git Bash 또는 WSL 환경을 사용할 수 있습니다. Git Bash 경로를 지정해야 한다면 PowerShell에서 다음을 설정합니다.

```powershell
$env:CLAUDE_CODE_GIT_BASH_PATH = "C:\Program Files\Git\bin\bash.exe"
```

프로젝트에서 Claude Code를 시작합니다.

```powershell
cd C:\path\to\your-project
claude
```

LocalAIAssistant로 팩을 만든 뒤 Claude Code에 붙여 넣는 과정은 Codex와 같습니다.

### Claude Code 자동 연동 (MCP 서버, 권장)

매번 명령을 실행하고 복사·붙여넣기를 하지 않으려면, LocalAIAssistant를 MCP 서버로 등록해서
Claude Code가 필요할 때 로컬 Ollama를 직접 호출하게 만들 수 있습니다.

```powershell
pip install -r C:\path\to\LocalAIAssistant\requirements.txt
```

작업할 프로젝트 폴더 최상위에 `.mcp.json`을 만들거나, 이미 있다면 `mcpServers`에 아래 항목을 추가합니다.

```json
{
  "mcpServers": {
    "local-ai-assistant": {
      "command": "python",
      "args": ["C:\\path\\to\\LocalAIAssistant\\local_ai_mcp_server.py"]
    }
  }
}
```

`C:\path\to\LocalAIAssistant`는 실제로 이 저장소를 내려받은 경로로 바꿉니다. 이후 해당 프로젝트에서
`claude`를 실행하면 다음 세 가지 도구를 Claude Code가 직접 호출할 수 있습니다.

- `local_ai_doctor`: Ollama 연결과 모델 설치 상태 확인
- `local_ai_ask`: 저장소 파일이 필요 없는 간단한 질문(설명, 문법, 형식 변환 등)에 로컬 모델이 바로 답변
- `local_ai_pack`: 질문과 관련된 파일만 골라 로컬 모델이 요약한 컨텍스트 팩을 반환

Claude Code는 각 도구의 설명을 읽고 언제 사용할지 스스로 판단합니다. 단순 조회·설명처럼 저장소
탐색이 필요 없는 작업은 `local_ai_ask`로 로컬에서 끝내고, 저장소 근거가 필요한 질문에는 먼저
`local_ai_pack`으로 관련 파일을 좁힌 뒤 답하도록 유도하려면, 작업 중인 프로젝트의 `CLAUDE.md`에
다음과 같이 적어 두는 것을 권장합니다.

```markdown
## 로컬 AI 도구

- 저장소 파일이 필요 없는 간단한 질문/설명/형식 변환은 local_ai_ask를 먼저 사용하세요.
- 저장소 근거가 필요한 질문은 local_ai_pack으로 관련 파일을 좁힌 뒤 답하세요.
- 위 도구 호출이 실패하면 local_ai_doctor로 원인을 확인하세요.
```

파일 수정·Git 작업·테스트 실행은 여전히 Claude Code가 직접 수행합니다. 이 도구들은 탐색과
요약만 로컬로 옮길 뿐입니다.

## 5. 선택 방식: 에이전트 자체를 Ollama 로컬 모델로 실행

이 방식은 Codex/Claude Code의 클라우드 모델 대신 Ollama 모델을 사용합니다. 비용은 줄일 수 있지만 모델 성능, 긴 컨텍스트, 도구 호환성이 달라질 수 있으므로 처음에는 3번의 요약 팩 방식을 권장합니다.

최신 Ollama에서는 다음과 같이 통합 설정을 시작할 수 있습니다.

```powershell
# Codex CLI를 Ollama 모델로 실행
ollama launch codex

# Claude Code를 Ollama 모델로 실행
ollama launch claude
```

설정만 하고 바로 실행하지 않으려면 다음을 사용합니다.

```powershell
ollama launch codex --config
```

Ollama 통합은 코딩 에이전트에 큰 컨텍스트를 요구할 수 있습니다. 모델을 직접 연결할 때는 Ollama 공식 통합 문서의 컨텍스트 길이와 지원 모델을 확인하세요.

## 6. 매일 쓰는 명령

```powershell
# Ollama와 모델 상태 확인
python C:\path\to\LocalAIAssistant\local_assistant.py doctor

# 질문으로 관련 파일을 찾아 요약하고 클립보드에 복사
C:\path\to\LocalAIAssistant\Ask-LocalAssistant.ps1 `
  -Question "이번 테스트 실패의 원인과 수정 후보를 요약해줘" `
  -Path C:\path\to\your-project `
  -Copy

# 모델 없이 파일 선별만 확인
C:\path\to\LocalAIAssistant\Ask-LocalAssistant.ps1 `
  -Question "설정 로딩 흐름을 찾아줘" `
  -Path C:\path\to\your-project `
  -NoModel
```

## 7. 문제 해결

### `ollama`를 찾을 수 없음

Ollama 설치 후 PowerShell을 새로 열고 다시 실행합니다. 그래도 안 되면 Ollama 앱이 실행 중인지 확인합니다.

### 모델이 없다고 나옴

```powershell
ollama pull qwen2.5-coder:7b
ollama list
```

### 팩이 너무 길거나 관련 파일이 부족함

질문을 더 구체적으로 작성하거나 제한을 조정합니다.

```powershell
python local_assistant.py pack `
  --path C:\path\to\your-project `
  --question "WaveManager의 웨이브 생성과 PlayMode 테스트만 찾아줘" `
  --max-files 10 `
  --max-chars 50000 `
  --no-cache
```

생성된 팩은 참고 자료입니다. 실제 수정·Git 작업·테스트 실행 전에는 Codex 또는 Claude Code가 원본 파일을 다시 확인해야 합니다.

## 공식 문서

- [Codex CLI](https://developers.openai.com/codex/cli)
- [Codex 로그인](https://learn.chatgpt.com/docs/developer-commands?surface=cli#cli-codex-login)
- [Claude Code 설치](https://docs.anthropic.com/en/docs/claude-code/getting-started)
- [Ollama Codex 통합](https://docs.ollama.com/integrations/codex)
- [Ollama Claude Code 통합](https://docs.ollama.com/integrations/claude-code)
