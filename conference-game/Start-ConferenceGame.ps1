$ErrorActionPreference = 'Stop'
$gameDir = $PSScriptRoot
$rootDir = Split-Path -Parent $gameDir
$port = 8765

Start-Process -FilePath 'python' `
  -ArgumentList @('-m', 'http.server', "$port", '--bind', '127.0.0.1') `
  -WorkingDirectory $rootDir `
  -WindowStyle Hidden

Start-Process "http://127.0.0.1:$port/conference-game/"
