param(
    [Parameter(Mandatory = $true)][string]$Question,
    [string]$Path = (Get-Location).Path,
    [string]$Model = 'qwen2.5-coder:7b',
    [string]$Output = '.local-ai\context-pack.md',
    [switch]$NoModel,
    [switch]$NoCache,
    [switch]$Copy
)

$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$script = Join-Path $PSScriptRoot 'local_assistant.py'
$arguments = @(
    $script, 'pack',
    '--question', $Question,
    '--path', $Path,
    '--model', $Model,
    '--output', $Output
)
if ($NoModel) {
    $arguments += '--no-model'
}
if ($NoCache) {
    $arguments += '--no-cache'
}
if ($Copy) {
    $arguments += '--copy'
}

python @arguments
exit $LASTEXITCODE
