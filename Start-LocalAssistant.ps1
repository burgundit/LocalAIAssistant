param(
    [string]$Model = 'qwen2.5-coder:7b',
    [switch]$Doctor
)

$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$script = Join-Path $PSScriptRoot 'local_assistant.py'

if ($Doctor) {
    python $script doctor --model $Model
    exit $LASTEXITCODE
}

Write-Host 'Lumi (루미) 준비 완료.'
Write-Host "모델: $Model"
Write-Host '사용 예:'
Write-Host '.\Ask-LocalAssistant.ps1 -Question "질문" -Path C:\path\to\project'
python $script doctor --model $Model
