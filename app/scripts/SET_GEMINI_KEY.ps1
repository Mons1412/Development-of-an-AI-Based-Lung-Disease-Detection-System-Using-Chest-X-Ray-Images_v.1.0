
param(
  [string]$ProjectRoot = (Get-Location).Path
)

$ErrorActionPreference = "Stop"
Set-Location $ProjectRoot

$EnvPath = Join-Path $ProjectRoot ".env"
$ExamplePath = Join-Path $ProjectRoot ".env.example"

if (-not (Test-Path $EnvPath)) {
  if (Test-Path $ExamplePath) {
    Copy-Item $ExamplePath $EnvPath
  }
  else {
    New-Item -ItemType File -Path $EnvPath | Out-Null
  }
}

$secureKey = Read-Host "Dán API key Gemini MỚI (ký tự sẽ không hiển thị)" -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)

try {
  $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
}
finally {
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
}

if ([string]::IsNullOrWhiteSpace($plainKey)) {
  throw "API key không được để trống."
}

$values = [ordered]@{
  "ONLINE_AI_ENABLED" = "true"
  "AI_PRIMARY_PROVIDER" = "gemini"
  "GEMINI_API_KEY" = $plainKey.Trim()
  "GEMINI_MODEL" = "gemini-3.5-flash"
  "ONLINE_AI_TIMEOUT_SECONDS" = "30"
  "ONLINE_AI_TEMPERATURE" = ""
  "ONLINE_AI_MAX_ANSWER_CHARACTERS" = "6000"
  "AI_OFFLINE_FALLBACK_ENABLED" = "true"
}

$lines = if (Test-Path $EnvPath) { Get-Content $EnvPath } else { @() }

foreach ($name in $values.Keys) {
  $pattern = "^\s*" + [regex]::Escape($name) + "\s*="
  $replacement = "$name=$($values[$name])"
  $found = $false

  for ($index = 0; $index -lt $lines.Count; $index++) {
    if ($lines[$index] -match $pattern) {
      $lines[$index] = $replacement
      $found = $true
      break
    }
  }

  if (-not $found) {
    $lines += $replacement
  }
}

$lines | Set-Content -Path $EnvPath -Encoding utf8
$plainKey = $null

Write-Host "[PASS] Đã lưu Gemini key vào .env cục bộ." -ForegroundColor Green
Write-Host "[PASS] Key không được in ra terminal và không nằm trong source patch." -ForegroundColor Green
Write-Host "Tiếp theo chạy: python .\scripts\test_gemini_connection.py"
