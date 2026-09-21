from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
hud=(ROOT/'scripts/hud.gd').read_text()
view=(ROOT/'scripts/audio_debug_view_v69.gd').read_text()
ambient=(ROOT/'scripts/legacy_ambient_audio.gd').read_text()
checks={
 'f8_toggle':'KEY_F8' in hud and 'audio_debug_visible = not audio_debug_visible' in hud,
 'shadow_snapshot':'get_debug_snapshot' in hud and 'classic_parity_v68' in view,
 'fields':all(x in view for x in ['legacy_position','distance','listener_heading_deg','source_heading_deg','folded_angle_deg','pan','rear_mode_divisor','volume']),
 'reconstruction_fields':all(x in view for x in ['emitter_id','sound_id','asset','provenance','confidence','Logical event trace']),
 'logical_trace_wired':'LegacyEvents.captured_audio()' in hud,
 'mode_visible':'Runtime mode:' in view,
 'confidence_boundary':'PROVISIONAL' in view and 'HIGH' in view and 'approximate' in view,
 'slot_sort':'legacy_3d_slot' in view and 'sort_custom' in view,
 'ambient_shadow_present':'ClassicParity.evaluate' in ambient,
 'no_playback_mutation':'.volume_db' not in view and '.panning_strength' not in view,
}
out={'version':69,'checks':checks,'pass':all(checks.values())}
(ROOT/'data/audio/audio_debug_view_validation_v69.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
raise SystemExit(0 if out['pass'] else 1)
