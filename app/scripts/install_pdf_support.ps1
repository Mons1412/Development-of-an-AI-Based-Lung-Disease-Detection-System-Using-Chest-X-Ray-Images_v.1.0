$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Khong tim thay Python cua .venv tai: $Python"
}

& $Python -m pip install --upgrade pip
& $Python -m pip install "reportlab>=4.2,<5.0"
& $Python -m pip install -e $ProjectRoot
& $Python -c "import reportlab; print('ReportLab', reportlab.Version)"

Write-Host "PDF support installed successfully." -ForegroundColor Green
