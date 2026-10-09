#!/usr/bin/env python3
"""Source-pinned Well Room plaque sequence, branch and sample order contract."""
import hashlib,os,re,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_well_interaction_source_v363 import derive,SOURCE,EXPECTED
from analyze_world_runtime_serialization_v106 import parse_world
CORPUS=Path(os.environ.get("OPENAZRAEL_CORPUS",
  "F:/OpenRemaster/sources/materialized/openazrael_demo_atdemo_v1/bf0c87f731bb4e87/layer2/ATDEMO"))
README_SHA="2976197be180e90d9370c580d5f07491c84d459d9f1e26ada58e993a1230adc2"
class PlaqueOrder(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.readme=(CORPUS/"README.TXT").read_bytes()
  cls.world=SOURCE.read_bytes()
  cls.groups={(g["node"],g["slot"]):g for g in derive(cls.world)}
 def test_authoritative_readme_hash(self):
  self.assertEqual(hashlib.sha256(self.readme).hexdigest(),README_SHA)
 def test_authoritative_world_hash(self):
  self.assertEqual(hashlib.sha256(self.world).hexdigest(),EXPECTED)
 def test_explicit_readme_three_actions(self):
  text=" ".join(self.readme.decode("latin1").split()).casefold()
  phrases=("use the right-most lever to pull the right pipe out",
    "the lower right wheel to rotate it","and the lever again to put it back into the new hole")
  prior=-1
  for phrase in phrases:
   pos=text.find(phrase)
   self.assertGreater(pos,prior)
   prior=pos
 def test_zero_initialized_source_state_count(self):
  sec=parse_world(self.world)["sections"][4]
  self.assertEqual((sec["count"],sec["stream_records"]),(101,0))
 def test_first_lever_pulls_last_pushes(self):
  initial=self.groups[(16,1)]
  reverse=self.groups[(16,0)]
  self.assertEqual((initial["condition"]["opcode"],initial["condition"]["state_index_candidate"]),(10,46))
  self.assertEqual((reverse["condition"]["opcode"],reverse["condition"]["state_index_candidate"]),(4,46))
  self.assertEqual([(a["kind"],a.get("source_stem")) for a in initial["actions"] if a["kind"]=="sound"],[("sound","981pull")])
  self.assertEqual([(a["kind"],a.get("source_stem")) for a in reverse["actions"] if a["kind"]=="sound"],[("sound","982push")])
 def test_state46_transitions(self):
  self.assertEqual([(a["source_state_index"],a["source_state_value"]) for a in self.groups[(16,1)]["actions"] if a["kind"]=="state_write"],[(46,1),(42,0),(43,0)])
  self.assertEqual([(a["source_state_index"],a["source_state_value"]) for a in self.groups[(16,0)]["actions"] if a["kind"]=="state_write"],[(46,0)])
 def test_right_wheel_has_original_turn_sample_but_direction_holds(self):
  self.assertEqual([a["sound_file"] for a in self.groups[(13,0)]["actions"] if a["kind"]=="sound"],["977TURN.WAV"])
  self.assertEqual([a["sound_file"] for a in self.groups[(14,0)]["actions"] if a["kind"]=="sound"],["977TURN.WAV"])
 def test_production_sound_dispatch_semantics(self):
  project=Path(__file__).resolve().parents[1]
  src=(project/"scripts/r7_switch_control.gd").read_text(encoding="utf8")
  self.assertRegex(src,r'step_before == 0[\s\S]{0,130}R7_SWITCH_LEVER_PULL_SOUND')
  self.assertRegex(src,r'step_before == 2[\s\S]{0,130}R7_SWITCH_LEVER_PUSH_SOUND')
  self.assertRegex(src,r'R7SwitchStep"[\s\S]{0,50}== 2 else "PULL"')
 def test_source_step_selector_order(self):
  project=Path(__file__).resolve().parents[1]
  src=(project/"scripts/r7_source_action_selector_v359.gd").read_text(encoding="utf8")
  self.assertRegex(src,r'0:\s*return select_actions\(16, 1\)')
  self.assertRegex(src,r'2:\s*return select_actions\(16, 0\)')
  guard=(project/"scripts/r7_action_activation_guard_v360.gd").read_text(encoding="utf8")
  self.assertIn('0: {"node":16,"slot":1,"count":2}',guard)
  self.assertIn('2: {"node":16,"slot":0,"count":2}',guard)
  self.assertIn('return false',guard)
if __name__=="__main__":unittest.main(verbosity=2)