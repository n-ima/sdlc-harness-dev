# Mirrors the windows-latest job of harness-ci.yml:
#   1. run every .ps1 hook (except selftest.ps1) with a sample payload; must not crash,
#      output must be empty or valid JSON
#   2. inject-progress.ps1 positive check with a learnings.md fixture (no BOM, LF, Japanese)
# Run with cwd = harness root (scripts/check.py does this). ASCII-only on purpose
# so PowerShell 5.1 reads it correctly without a BOM.

$ErrorActionPreference = 'Continue'
# Hooks emit UTF-8 (no BOM). Decode child output as UTF-8, otherwise PowerShell 5.1 on a
# CP932 console mangles Japanese and the JSON check fails.
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false } catch {}
try { [Console]::InputEncoding = New-Object System.Text.UTF8Encoding $false } catch {}
$fail = 0

$payload = '{"tool_input":{"command":"git status","file_path":"src/app.ts","content":"hello"}}'
Get-ChildItem .github/hooks/scripts/*.ps1 | Where-Object { $_.Name -ne 'selftest.ps1' } | ForEach-Object {
  $name = $_.Name
  $out = ($payload | powershell.exe -NoProfile -ExecutionPolicy Bypass -File $_.FullName | Out-String).Trim()
  if ($LASTEXITCODE -ne 0) { Write-Host "CRASH: $name (exit=$LASTEXITCODE)"; $fail = 1 }
  if ($out) {
    try { $null = $out | ConvertFrom-Json; Write-Host "OK (json): $name" }
    catch { Write-Host "INVALID JSON: $name -> $out"; $fail = 1 }
  } else {
    Write-Host "OK (empty): $name"
  }
}

# --- inject-progress.ps1 positive check ---
$harness = (Get-Location).Path
$fix = Join-Path $env:TEMP ("injfix-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force (Join-Path $fix 'docs/00-overview') | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$learnings = "## " + [char]0x6559 + [char]0x8A13 + "`n- [W1] " + [char]0x65E5 + [char]0x672C + [char]0x8A9E + " D:\proj\x`n"
[System.IO.File]::WriteAllText((Join-Path $fix 'docs/00-overview/learnings.md'), $learnings, $utf8NoBom)
try {
  Set-Location $fix
  $out = (powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $harness '.github/hooks/scripts/inject-progress.ps1') | Out-String).Trim()
  if ($LASTEXITCODE -ne 0) { Write-Host "inject-progress CRASH (exit=$LASTEXITCODE)"; $fail = 1 }
  elseif (-not $out) { Write-Host "inject-progress EMPTY OUTPUT"; $fail = 1 }
  else {
    try {
      $obj = $out | ConvertFrom-Json
      $ctx = [string]$obj.hookSpecificOutput.additionalContext
      if ($ctx -like '*[W1]*') { Write-Host "OK (inject-progress positive)" }
      else { Write-Host "inject-progress: learnings not injected -> $ctx"; $fail = 1 }
    } catch { Write-Host "inject-progress INVALID JSON: $out"; $fail = 1 }
  }
} finally {
  Set-Location $harness
  Remove-Item -Recurse -Force $fix -ErrorAction SilentlyContinue
}

exit $fail
