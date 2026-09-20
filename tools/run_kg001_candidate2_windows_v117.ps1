[CmdletBinding()]
param(
    [string]$DemoDir = "",
    [string]$Godot = $env:GODOT_BIN,
    [string]$Python = "python",
    [switch]$SkipRestore,
    [switch]$PromoteResults,
    [switch]$SkipExport,
    [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

function Invoke-Checked {
    param(
        [Parameter(Mandatory=$true)][string]$Executable,
        [Parameter(Mandatory=$true)][string[]]$Arguments
    )
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed ($LASTEXITCODE): $Executable $($Arguments -join ' ')"
    }
}

$requiredSource = @(
    "tools/restore_candidate_assets.py",
    "tools/run_kg001_candidate_v112.py",
    "tools/validate_kg001_toolchain_v117.py",
    "tools/write_kg001_build_manifest.py",
    "export_presets.cfg",
    "data/tests/kg001_toolchain_contract_v117.json",
    "scripts/kg001_visual_capture_v117.gd"
)
$missingSource = @($requiredSource | Where-Object { -not (Test-Path $_) })

if ($ValidateOnly) {
    $validation = [ordered]@{
        schema = "openazrael.kg001.candidate2_windows_wrapper_source"
        version = 117
        status = $(if ($missingSource.Count -eq 0) { "PASS" } else { "FAIL" })
        required_source = $requiredSource
        missing_source = $missingSource
        canonical_runner = "tools/run_kg001_candidate_v112.py"
        graphical_capture_flag = "--visual-capture"
        fresh_checkout_flag = "--fresh-checkout"
        export_preset = "Windows Candidate 2"
        commercial_assets_embedded = $false
    }
    $validation | ConvertTo-Json -Depth 5
    if ($missingSource.Count -ne 0) { exit 1 }
    exit 0
}

if ($missingSource.Count -ne 0) {
    throw "Candidate 2 wrapper source is incomplete: $($missingSource -join ', ')"
}

if ([string]::IsNullOrWhiteSpace($Godot)) {
    foreach ($candidate in @("godot4.exe", "godot.exe", "godot4", "godot")) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($null -ne $command) {
            $Godot = $command.Source
            break
        }
    }
}
if ([string]::IsNullOrWhiteSpace($Godot)) {
    throw "Godot was not supplied and GODOT_BIN/godot executable was not found."
}

# Fail early on any local toolchain drift. The canonical runner repeats this
# check, deliberately keeping this wrapper thin rather than reimplementing it.
Invoke-Checked $Python @(
    "tools/validate_kg001_toolchain_v117.py",
    "--godot", $Godot,
    "--require-godot"
)

if (-not $SkipRestore) {
    if ([string]::IsNullOrWhiteSpace($DemoDir)) {
        throw "-DemoDir is required unless -SkipRestore is used."
    }
    $resolvedDemo = (Resolve-Path $DemoDir).Path
    Invoke-Checked $Python @(
        "tools/restore_candidate_assets.py",
        $resolvedDemo
    )
}

$candidateArgs = @(
    "tools/run_kg001_candidate_v112.py",
    "--godot", $Godot,
    "--fresh-checkout",
    "--visual-capture"
)
if ($PromoteResults) {
    $candidateArgs += "--promote-results"
}
Invoke-Checked $Python $candidateArgs

if (-not $SkipExport) {
    New-Item -ItemType Directory -Force -Path "exports" | Out-Null
    Invoke-Checked $Godot @(
        "--headless",
        "--path", ".",
        "--export-debug", "Windows Candidate 2"
    )

    $exe = Join-Path $Root "exports/OpenAzrael-KG001-Candidate2-v116.exe"
    $pck = Join-Path $Root "exports/OpenAzrael-KG001-Candidate2-v116.pck"
    if (-not (Test-Path $exe)) {
        throw "Expected Candidate 2 executable was not exported: $exe"
    }
    if (-not (Test-Path $pck)) {
        throw "Expected Candidate 2 PCK was not exported: $pck"
    }

    New-Item -ItemType Directory -Force -Path ".tmp/kg001" | Out-Null
    $exportEvidence = [ordered]@{
        schema = "openazrael.kg001.windows_candidate2_export"
        version = 117
        status = "PASS"
        preset = "Windows Candidate 2"
        executable = "exports/OpenAzrael-KG001-Candidate2-v116.exe"
        executable_size_bytes = (Get-Item $exe).Length
        executable_sha256 = (Get-FileHash -Algorithm SHA256 $exe).Hash.ToLowerInvariant()
        pck = "exports/OpenAzrael-KG001-Candidate2-v116.pck"
        pck_size_bytes = (Get-Item $pck).Length
        pck_sha256 = (Get-FileHash -Algorithm SHA256 $pck).Hash.ToLowerInvariant()
        build_manifest = "data/generated/kg001_candidate_build_manifest.json"
        source_safe_metadata_only = $true
    }
    $exportEvidence |
        ConvertTo-Json -Depth 5 |
        Set-Content -Encoding utf8 ".tmp/kg001/kg001_windows_candidate2_export_v117.json"
    $exportEvidence | ConvertTo-Json -Depth 5
}

Write-Host "OpenAzrael KG-001 Candidate 2 local Windows cycle completed."
