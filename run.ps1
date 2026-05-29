param(
    [switch]$Gui,
    [switch]$Debug
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv is not installed." -ForegroundColor Yellow
    Write-Host "Install it with:"
    Write-Host 'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"'
    exit 1
}

if ($Debug) {
    uv run python UstcNetwork.py --debug-login ustc-network.conf
} elseif ($Gui) {
    uv run --extra gui python UstcNetwork_GUI.py
} else {
    uv run python UstcNetwork.py ustc-network.conf
}
