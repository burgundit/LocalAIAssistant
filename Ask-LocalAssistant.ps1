param(
    [Parameter(Mandatory = $true)][string]$Question,
    [string]$Path = (Get-Location).Path,
    [string]$Model = 'qwen2.5-coder:7b',
    [string]$Output = '.local-ai\context-pack.md',
    [switch]$NoModel,
    [switch]$NoCache,
    [switch]$Copy,
    [int]$MaxFiles,
    [int]$MaxChars,
    [int]$MaxCharsPerFile
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
if ($MaxFiles -gt 0) {
    $arguments += @('--max-files', $MaxFiles)
}
if ($MaxChars -gt 0) {
    $arguments += @('--max-chars', $MaxChars)
}
if ($MaxCharsPerFile -gt 0) {
    $arguments += @('--max-chars-per-file', $MaxCharsPerFile)
}

python @arguments
exit $LASTEXITCODE
