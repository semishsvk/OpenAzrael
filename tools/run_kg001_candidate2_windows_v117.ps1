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
    "tools/validate_kg001_candidate2_asset_set_v118.py",
    "tools/validate_kg001_build_manifest_v118.py",
    "tools/promote_kg001_candidate_results_v118.py",
    "data/tests/kg001_test_build_contract_v118.json",
    "tools/validate_kg001_test_build_contract_v118.py",
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

if ($PromoteResults -and $SkipExport) {
    throw "-PromoteResults cannot be combined with -SkipExport. Windows wrapper promotion is allowed only after export + exported-EXE startup smoke."
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
Invoke-Checked $Python $candidateArgs

$buildManifestPath = Join-Path $Root "data/generated/kg001_candidate_build_manifest.json"
if (-not (Test-Path $buildManifestPath)) {
    throw "Candidate build manifest missing after canonical runner: $buildManifestPath"
}
$buildManifest = Get-Content -Raw $buildManifestPath | ConvertFrom-Json
$currentHead = (& git rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($currentHead)) {
    throw "Unable to resolve current Git HEAD for Candidate build identity."
}
if ($buildManifest.commit_sha -ne $currentHead) {
    throw "Build manifest commit does not match current HEAD: $($buildManifest.commit_sha) != $currentHead"
}
if (-not $buildManifest.source_identity_complete) {
    throw "Build manifest source identity is incomplete."
}
if (-not $buildManifest.asset_counts_complete) {
    throw "Build manifest asset counts are incomplete; refusing Windows export."
}
if ($buildManifest.godot.status -ne "PASS") {
    throw "Build manifest Godot identity did not PASS."
}

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
    $startupLog = Join-Path $Root ".tmp/kg001/kg001_windows_candidate2_startup.log"
    if (Test-Path $startupLog) {
        Remove-Item -Force $startupLog
    }
    & $exe "--headless" "--quit-after" "120" "--log-file" $startupLog
    $startupExit = $LASTEXITCODE
    if ($startupExit -ne 0) {
        throw "Exported Candidate 2 startup smoke failed with exit code $startupExit."
    }
    if (-not (Test-Path $startupLog)) {
        throw "Exported Candidate 2 startup smoke did not produce a log."
    }
    $startupText = Get-Content -Raw $startupLog
    $criticalPatterns = @(
        "SCRIPT ERROR:",
        "ERROR: Failed to load script",
        "ERROR: Failed to create an autoload",
        "ERROR: Failed to load resource",
        "ERROR: Cannot open file"
    )
    $criticalHits = @(
        foreach ($pattern in $criticalPatterns) {
            if ($startupText.Contains($pattern)) { $pattern }
        }
    )
    if ($criticalHits.Count -ne 0) {
        throw "Exported Candidate 2 startup log contains critical errors: $($criticalHits -join ', ')"
    }
    $startupMarker = "OPENAZRAEL_CANDIDATE_STARTUP_READY"
    if (-not $startupText.Contains($startupMarker)) {
        throw "Exported Candidate 2 startup marker was not observed."
    }
    if (-not $startupText.Contains($currentHead)) {
        throw "Exported Candidate 2 startup marker/log does not contain current build commit $currentHead."
    }

    $candidateEvidencePath = Join-Path $Root ".tmp/kg001/kg001_candidate_v112.json"
    $freshEvidencePath = Join-Path $Root ".tmp/kg001/kg001_fresh_checkout.json"
    $visualEvidencePath = Join-Path $Root ".tmp/kg001/kg001_visual_capture_v117.json"
    $candidateEvidence = Get-Content -Raw $candidateEvidencePath | ConvertFrom-Json
    $freshEvidence = Get-Content -Raw $freshEvidencePath | ConvertFrom-Json
    $visualEvidence = Get-Content -Raw $visualEvidencePath | ConvertFrom-Json
    if ($candidateEvidence.status -ne "PASS") {
        throw "Canonical Candidate suite did not record PASS."
    }
    if ($freshEvidence.status -ne "PASS") {
        throw "Fresh-checkout evidence did not record PASS."
    }
    if ($candidateEvidence.commit_sha -ne $currentHead) {
        throw "Candidate evidence commit does not match current HEAD."
    }
    if ($freshEvidence.commit_sha -ne $currentHead) {
        throw "Fresh-checkout evidence commit does not match current HEAD."
    }
    if ($visualEvidence.status -ne "PASS") {
        throw "Canonical visual capture evidence did not record PASS."
    }
    if ($visualEvidence.build_commit_sha -ne $currentHead) {
        throw "Visual-capture evidence commit does not match current HEAD."
    }
    if ([string]::IsNullOrWhiteSpace([string]$visualEvidence.run_id)) {
        throw "Visual-capture evidence has no run_id."
    }
    $captureRows = @($visualEvidence.captures)
    if ($captureRows.Count -ne 3) {
        throw "Visual-capture evidence must contain exactly 3 canonical captures."
    }
    $expectedCaptures = @{
        "R1" = "spaview"
        "R7" = "view"
        "R8" = "Object14"
    }
    foreach ($room in $expectedCaptures.Keys) {
        $match = @(
            $captureRows | Where-Object {
                $_.room -eq $room -and $_.view -eq $expectedCaptures[$room]
            }
        )
        if ($match.Count -ne 1) {
            throw "Visual-capture evidence missing/duplicated canonical $room/$($expectedCaptures[$room]) capture."
        }
        if ([string]$match[0].sha256 -notmatch "^[0-9a-f]{64}$") {
            throw "Visual-capture evidence has invalid SHA-256 for $room."
        }
        if ([int]$match[0].width -ne 1280 -or [int]$match[0].height -ne 720) {
            throw "Visual-capture evidence has unexpected dimensions for $room."
        }
    }
    $visualEvidenceSha256 = (Get-FileHash -Algorithm SHA256 $visualEvidencePath).Hash.ToLowerInvariant()

    $distributionBuildManifest = Join-Path $Root "exports/OpenAzrael-KG001-Candidate2-v116.build-manifest.json"
    Copy-Item -Force $buildManifestPath $distributionBuildManifest
    $distributionBuildManifestSha256 = (Get-FileHash -Algorithm SHA256 $distributionBuildManifest).Hash.ToLowerInvariant()
    $sourceBuildManifestSha256 = (Get-FileHash -Algorithm SHA256 $buildManifestPath).Hash.ToLowerInvariant()
    if ($distributionBuildManifestSha256 -ne $sourceBuildManifestSha256) {
        throw "Distributed build-manifest sidecar does not match the manifest embedded for export."
    }

    $exportEvidence = [ordered]@{
        schema = "openazrael.kg001.windows_candidate2_export"
        version = 118
        status = "PASS"
        preset = "Windows Candidate 2"
        commit_sha = $currentHead
        executable = "exports/OpenAzrael-KG001-Candidate2-v116.exe"
        executable_size_bytes = (Get-Item $exe).Length
        executable_sha256 = (Get-FileHash -Algorithm SHA256 $exe).Hash.ToLowerInvariant()
        pck = "exports/OpenAzrael-KG001-Candidate2-v116.pck"
        pck_size_bytes = (Get-Item $pck).Length
        pck_sha256 = (Get-FileHash -Algorithm SHA256 $pck).Hash.ToLowerInvariant()
        build_manifest = "data/generated/kg001_candidate_build_manifest.json"
        build_manifest_sha256 = $sourceBuildManifestSha256
        distribution_build_manifest = "exports/OpenAzrael-KG001-Candidate2-v116.build-manifest.json"
        distribution_build_manifest_sha256 = $distributionBuildManifestSha256
        startup_smoke = [ordered]@{
            status = "PASS"
            exit_code = $startupExit
            log = ".tmp/kg001/kg001_windows_candidate2_startup.log"
            log_sha256 = (Get-FileHash -Algorithm SHA256 $startupLog).Hash.ToLowerInvariant()
            critical_error_hits = $criticalHits
            startup_marker = $startupMarker
            build_commit_observed = $currentHead
        }
        source_safe_metadata_only = $true
    }

    $receipt = [ordered]@{
        schema = "openazrael.kg001.test_build_receipt"
        version = 118
        status = "READY_FOR_G10_MANUAL_TEST"
        build_id = "KG-001 Candidate 2"
        checkpoint = "v116-context-v31"
        commit_sha = $currentHead
        candidate_suite_status = $candidateEvidence.status
        fresh_checkout_status = $freshEvidence.status
        visual_capture_status = $visualEvidence.status
        visual_capture_run_id = $visualEvidence.run_id
        visual_capture_evidence_sha256 = $visualEvidenceSha256
        visual_captures = $captureRows
        candidate2_asset_set_status = $candidateEvidence.candidate2_asset_set
        candidate2_asset_local_status = $candidateEvidence.candidate2_asset_local_status
        godot = $buildManifest.godot
        runtime_source_aggregate_sha256 = $buildManifest.runtime_source_identity.aggregate_sha256
        source_contracts_aggregate_sha256 = $buildManifest.source_contracts.aggregate_sha256
        rooms_aggregate_sha256 = $buildManifest.assets.rooms.aggregate_sha256
        audio_aggregate_sha256 = $buildManifest.assets.audio.aggregate_sha256
        classic_textures_aggregate_sha256 = $buildManifest.assets.classic_textures.aggregate_sha256
        executable_sha256 = $exportEvidence.executable_sha256
        pck_sha256 = $exportEvidence.pck_sha256
        distribution_build_manifest = $exportEvidence.distribution_build_manifest
        distribution_build_manifest_sha256 = $exportEvidence.distribution_build_manifest_sha256
        checksum_manifest = "exports/OpenAzrael-KG001-Candidate2-v116.SHA256SUMS"
        startup_smoke = $exportEvidence.startup_smoke
        manual_pending = @(
            "G10 verify stable floor collision in R1/R7/R8",
            "G10 verify ambient/event audio is actually audible at expected volume",
            "G10 verify KEYHOLE#/tongs and other # cutouts have correct transparency with no pink/black fringe",
            "G10 complete the intended demo route and confirm zero reproducible softlocks"
        )
        release_blockers_close_automatically = $false
        demo_known_good_tag_allowed = $false
        source_safe_metadata_only = $true
    }

    $exportEvidence |
        ConvertTo-Json -Depth 8 |
        Set-Content -Encoding utf8 ".tmp/kg001/kg001_windows_candidate2_export_v118.json"
    $receipt |
        ConvertTo-Json -Depth 8 |
        Set-Content -Encoding utf8 ".tmp/kg001/kg001_test_build_receipt_v118.json"
    $receipt |
        ConvertTo-Json -Depth 8 |
        Set-Content -Encoding utf8 "exports/OpenAzrael-KG001-Candidate2-v116.test-build.json"

    $testingText = @"
OpenAzrael KG-001 Candidate 2
=============================

Checkpoint: v116-context-v31
Commit: $currentHead
Status: READY_FOR_G10_MANUAL_TEST
Godot: $($buildManifest.godot.version)
Visual capture run: $($visualEvidence.run_id)
Visual capture evidence SHA-256: $visualEvidenceSha256

Executable SHA-256:
$($exportEvidence.executable_sha256)

PCK SHA-256:
$($exportEvidence.pck_sha256)

IMPORTANT
---------
This is a TEST BUILD, not a known-good release.
Issues #6, #9 and #11 remain open until manual G10 passes.
Do not create or treat demo-known-good-001 as approved from this package alone.

MANUAL G10 CHECKLIST
--------------------
1. R1 / R7 / R8 floor collision:
   - verify the player does not fall through floors;
   - verify normal walking/standing at the canonical test locations.

2. Audio:
   - verify ambient audio is actually audible;
   - verify expected event audio is audible and not obviously distorted/silent.

3. Legacy cutout transparency:
   - inspect KEYHOLE#, rusty tongs/MINETON# and other # cutouts;
   - there must be no visible pink/magenta background;
   - there must be no obvious black fringe around the mask edge.

4. Demo route:
   - complete the intended KG-001 demo route;
   - confirm zero reproducible softlocks.

DIAGNOSTIC KEYS
---------------
F6  Trigger volume visualization
F7  Candidate diagnostic HUD
F8  Audio debug
F9  Audio parity capture
F10 Canonical state dump
F11 Source-safe bug-report ZIP

BUG REPORTING
-------------
If you find a reproducible defect:
1. reproduce it once;
2. press F11 as close to the failure as possible;
3. keep the generated ZIP from the Candidate run directory;
4. report the issue through the OpenAzrael GitHub bug template;
5. include exact reproduction steps and severity.

The F11 package contains source-safe telemetry/state/system evidence and does not
embed the excluded commercial room/audio/texture payloads.

BUILD IDENTITY
--------------
Runtime source aggregate:
$($buildManifest.runtime_source_identity.aggregate_sha256)

Source contracts aggregate:
$($buildManifest.source_contracts.aggregate_sha256)

Rooms aggregate:
$($buildManifest.assets.rooms.aggregate_sha256)

Audio aggregate:
$($buildManifest.assets.audio.aggregate_sha256)

Classic textures aggregate:
$($buildManifest.assets.classic_textures.aggregate_sha256)
"@
    $testingPath = Join-Path $Root "exports/OpenAzrael-KG001-Candidate2-v116.TESTING.txt"
    $testingText | Set-Content -Encoding utf8 $testingPath

    $receiptPath = Join-Path $Root "exports/OpenAzrael-KG001-Candidate2-v116.test-build.json"
    $checksumPath = Join-Path $Root "exports/OpenAzrael-KG001-Candidate2-v116.SHA256SUMS"
    $checksumFiles = @(
        $exe,
        $pck,
        $distributionBuildManifest,
        $receiptPath,
        $testingPath
    )
    $checksumLines = @(
        foreach ($file in $checksumFiles) {
            $hash = (Get-FileHash -Algorithm SHA256 $file).Hash.ToLowerInvariant()
            "$hash  $([System.IO.Path]::GetFileName($file))"
        }
    )
    $checksumLines | Set-Content -Encoding ascii $checksumPath

    $receipt | ConvertTo-Json -Depth 8
    Write-Host "Distribution checksum manifest:"
    Get-Content $checksumPath
}

if ($PromoteResults) {
    Invoke-Checked $Python @(
        "tools/promote_kg001_candidate_results_v118.py"
    )
}

Write-Host "OpenAzrael KG-001 Candidate 2 local Windows cycle completed."
