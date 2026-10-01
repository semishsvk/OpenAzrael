#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REGISTRY="$ROOT/toolchain/toolchain_registry_v1.json"
CACHE="${OPENAZRAEL_TOOLCHAIN_HOME:-$HOME/.openazrael/toolchains}"
GODOT_ZIP="${GODOT_ZIP:-$CACHE/downloads/Godot_v4.7.2-stable_linux.x86_64.zip}"
GODOT_DIR="$CACHE/godot/4.7.2"
GODOT_BIN="$GODOT_DIR/Godot_v4.7.2-stable_linux.x86_64"
EXPECTED_GODOT_SHA="cadd3204e728a35d3f13adb7fd0d7902636b79f6b95c40c265eb73b6c35329e4"

fail(){ echo "BLOCKED_TOOLCHAIN_UNAVAILABLE: $*" >&2; exit 2; }
need(){ command -v "$1" >/dev/null 2>&1 || fail "missing command: $1"; }
need python3
need sha256sum
need unzip

[[ -f "$GODOT_ZIP" ]] || fail "Godot archive cache miss. Materialize Drive file 1w6de416siM_c6xVgsA3gY2BmlnW0ruSo to $GODOT_ZIP; discovery search is forbidden."
echo "$EXPECTED_GODOT_SHA  $GODOT_ZIP" | sha256sum -c - || fail "Godot archive hash mismatch"
mkdir -p "$GODOT_DIR"
if [[ ! -x "$GODOT_BIN" ]]; then unzip -qo "$GODOT_ZIP" -d "$GODOT_DIR"; chmod +x "$GODOT_BIN"; fi
VERSION="$("$GODOT_BIN" --version | head -n1)"
[[ "$VERSION" == 4.7.2.stable* ]] || fail "unexpected Godot version: $VERSION"

SF2="${OPENAZRAEL_SOUNDFONT:-}"
[[ -n "$SF2" && -f "$SF2" ]] || fail "OPENAZRAEL_SOUNDFONT must point to pinned FluidR3_GM.sf2"
SF2_SHA="$(sha256sum "$SF2" | awk '{print $1}')"

FLUID_LIB="${OPENAZRAEL_FLUIDSYNTH_LIB:-}"
if [[ -z "$FLUID_LIB" ]]; then
  FLUID_LIB="$(ldconfig -p 2>/dev/null | awk '/libfluidsynth\.so/{print $NF; exit}')"
fi
[[ -n "$FLUID_LIB" && -f "$FLUID_LIB" ]] || fail "libfluidsynth native library unavailable"
FLUID_SHA="$(sha256sum "$FLUID_LIB" | awk '{print $1}')"

python3 - <<'PY' || fail "Python audio stack unavailable"
import numpy, soundfile
print("numpy="+numpy.__version__)
print("soundfile="+soundfile.__version__)
print("libsndfile="+str(getattr(soundfile,"__libsndfile_version__","UNKNOWN")))
PY

TEMPLATE_DIR="${GODOT4_EXPORT_TEMPLATES_DIR:-$HOME/.local/share/godot/export_templates/4.7.2.stable}"
[[ -f "$TEMPLATE_DIR/windows_release_x86_64.exe" ]] || fail "Godot 4.7.2 Windows x86_64 export template missing at $TEMPLATE_DIR"

mkdir -p "$ROOT/.tmp/kg001"
cat > "$ROOT/.tmp/kg001/c5_toolchain_receipt.json" <<EOF
{
  "schema":"openazrael.kg001.c5_toolchain_receipt",
  "version":1,
  "status":"PASS",
  "godot":{"path":"$GODOT_BIN","version":"$VERSION","archive_sha256":"$EXPECTED_GODOT_SHA"},
  "soundfont":{"path":"$SF2","sha256":"$SF2_SHA"},
  "fluidsynth":{"path":"$FLUID_LIB","sha256":"$FLUID_SHA"},
  "export_templates":{"path":"$TEMPLATE_DIR","windows_release_x86_64":true}
}
EOF
echo "C5_TOOLCHAIN_READY $ROOT/.tmp/kg001/c5_toolchain_receipt.json"
echo "export GODOT_BIN='$GODOT_BIN'"
echo "export OPENAZRAEL_SOUNDFONT='$SF2'"
echo "export OPENAZRAEL_FLUIDSYNTH_LIB='$FLUID_LIB'"
