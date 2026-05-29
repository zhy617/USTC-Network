param(
    [switch]$Gui,
    [switch]$Build
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv is not installed." -ForegroundColor Yellow
    Write-Host "Install it with:"
    Write-Host 'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"'
    exit 1
}

if ($Build) {
    uv sync --extra build
} elseif ($Gui) {
    uv sync --extra gui
} else {
    uv sync
}
