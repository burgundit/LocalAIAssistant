# LocalAIAssistant

Codex와 Claude Code에 전체 저장소를 그대로 전달하지 않고, 로컬 Ollama 모델이 먼저 관련 파일을 고르고 압축하여 작은 컨텍스트 팩을 만드는 도구입니다.

## 권장 환경

- Windows 11
- Python 3.11 이상
- Ollama
- 첫 모델: `qwen2.5-coder:7b`

RTX 5070 12GB에서는 7B 모델이 속도와 품질의 균형이 좋습니다.

## 빠른 시작

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
