import json,tempfile,time,unittest,uuid
from pathlib import Path
from PIL import Image
from relay.service import PicoService
from relay.state import RelayState
from relay.tests.fake import FakeSupabase

ROOT=Path(__file__).resolve().parents[1]
MOODS=['angry','curious','happy','sleepy','surprised']
class MoodContractTests(unittest.TestCase):
 def test_new_moods_have_real_original_animation_assets(self):
  mapping={'angry':'stuck','curious':'thinking','happy':'done','sleepy':'idle','surprised':'needsYou'}
  for character in ('mica','tuck'):
   for mood,activity in mapping.items():
    with Image.open(ROOT/'assets/characters'/character/(activity+'.gif')) as image:
     self.assertEqual(image.format,'GIF')
     self.assertGreater(image.n_frames,1,character+' '+mood+' must remain animated')
     self.assertTrue((ROOT/'assets/characters'/character/(activity+'.png')).is_file())
 def test_every_mood_survives_real_relay_validation(self):
  with tempfile.TemporaryDirectory() as d:
   db=FakeSupabase();service=PicoService(db,RelayState(Path(d)/'state.sqlite'))
   device=str(uuid.uuid4());db.tables['devices'].append({'id':device,'user_id':'owner-1','name':'Pico · test','revoked_at':None})
   for character in ('mica','tuck'):
    for mood in MOODS:
     service.enqueue('owner-1',device,'companion',{'character':character,'mood':mood,'mood_until':str(int(time.time()*1000)+15000)})
     self.assertEqual(service.mailbox('owner-1',device)[0]['payload']['mood'],mood)
 def test_native_and_phone_accept_same_mood_names(self):
  for path in ('lib/services/pico_store.dart','agents/native/PicoOverlay.swift','agents/native/windows/Program.cs'):
   text=(ROOT/path).read_text()
   for mood in MOODS:self.assertIn(mood,text)
