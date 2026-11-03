import queue,sys,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from companion import Companion
class StepAwayOffline(unittest.TestCase):
    def test_context_detection_does_not_need_network(self):
        c=Companion.__new__(Companion)
        c.state={'notice_idle':True,'paused_until':0,'idle_minutes':1}
        c.events=queue.Queue()
        c.platform=SimpleNamespace(context=lambda:{'idle':70,'app':'TextEdit','title':'Lecture'})
        held=[];c.hold_context=lambda info:held.append(info)
        self.assertTrue(c.observe_step_away(False));self.assertEqual(len(held),1)
        self.assertTrue(c.observe_step_away(True));self.assertEqual(len(held),1)
        c.platform.context=lambda:{'idle':0}
        self.assertFalse(c.observe_step_away(True));self.assertEqual(c.events.get_nowait(),('return',None))
    def test_disabled_and_paused_do_not_capture(self):
        c=Companion.__new__(Companion);c.state={'notice_idle':False,'paused_until':0}
        self.assertFalse(c.observe_step_away(False))
        c.state={'notice_idle':True,'paused_until':10**12}
        self.assertFalse(c.observe_step_away(False))
