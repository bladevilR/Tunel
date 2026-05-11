param(
  [int]$Port = 8898
)

$ErrorActionPreference = "Stop"

$env:AMAP_JS_KEY = if ($env:AMAP_JS_KEY) { $env:AMAP_JS_KEY } else { [Environment]::GetEnvironmentVariable("AMAP_JS_KEY", "User") }
$env:AMAP_SECURITY_CODE = if ($env:AMAP_SECURITY_CODE) { $env:AMAP_SECURITY_CODE } else { [Environment]::GetEnvironmentVariable("AMAP_SECURITY_CODE", "User") }

if (-not $env:AMAP_JS_KEY) {
  throw "Please set AMAP_JS_KEY before running this demo."
}

if (-not $env:AMAP_SECURITY_CODE) {
  throw "Please set AMAP_SECURITY_CODE before running this demo."
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
python (Join-Path $scriptDir "serve_amap_sync.py") --host 127.0.0.1 --port $Port
