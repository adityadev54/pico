import json
import sys
import unittest
import queue
import threading
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'agents'))
from focus_gate import hold_result, may_run_focused
from companion import Companion

class FocusGateTests(unittest.TestCase):
    def test_durable_dedup_and_dismissal(self):
        state={'places':{},'focused':True}
        key=hold_result(state,'Saved','task1')
        hold_result(state,'Saved','task1');hold_result(state,'Saved','task2')
        self.assertEqual(len(state['places']),2)
        restored=json.loads(json.dumps(state))
        self.assertTrue(restored['focused'])
        restored['places'][key]['status']='finished'
        hold_result(restored,'Saved','task1')
        self.assertEqual(restored['places'][key]['status'],'finished')

    def test_focus_blocks_interrupting_mail_but_not_cancel_or_reads(self):
        for tool in ['fs_write','open_app','open_website','manage_permissions','process_run']:
            self.assertFalse(may_run_focused('tool_call',{'tool':tool}))
        for tool in ['fs_read','fs_list','search_documents']:
            self.assertTrue(may_run_focused('tool_call',{'tool':tool}))
        self.assertTrue(may_run_focused('cancel',{}))
        self.assertFalse(may_run_focused('skill_request',{'query':'teach'}))
        self.assertTrue(may_run_focused('skill_request',{'query':'run:123'}))

    def stub(self):
        c=Companion.__new__(Companion)
        c.state={'places':{},'focused':True,'notice_idle':True,'paused_until':0,'idle_minutes':1}
        c.save=Mock();c.overlay_message=Mock();c.load_character=Mock();c.overlay=True
        c.events=queue.Queue();c.lock=threading.RLock()
        return c

    def test_focused_completions_saved_without_overlay(self):
        c=self.stub();c.present('working','Preparing');c.present('happy','Done','task1')
        c.overlay_message.assert_not_called();self.assertEqual(len(c.state['places']),1)
        c.present('happy','Done','task1');self.assertEqual(len(c.state['places']),1)

    def test_one_minute_idle_transition_captures_once(self):
        c=self.stub();c.platform=Mock();c.hold_context=Mock()
        c.platform.context.return_value={'idle':59};self.assertFalse(c.observe_step_away(False))
        c.platform.context.return_value={'idle':60};self.assertTrue(c.observe_step_away(False))
        c.observe_step_away(True);c.hold_context.assert_called_once()
        c.platform.context.return_value={'idle':0};self.assertFalse(c.observe_step_away(True))
        self.assertEqual(c.events.get_nowait()[0],'return')

    def test_continue_only_uses_existing_app_approval(self):
        c=self.stub();c.state['allowed_apps']=[];c.open_application=Mock()
        c.reopen_approved('unknown.app');c.open_application.assert_not_called()

    def test_private_windows_never_capture(self):
        c=self.stub();c.state.update(snapshots=True,excluded_apps=[],outgoing=[])
        for info in [{'bundle':'com.apple.MobileSMS','app':'Messages','title':'Chat'},
                     {'bundle':'com.apple.Safari','app':'Safari','title':'Private Browsing'}]:
            c.hold_context({**info,'screen_access':True})
        c.platform=Mock() if not hasattr(c,'platform') else c.platform
        self.assertTrue(all(p['snapshot'] is None for p in c.state['places'].values()))

    def test_focus_toggle_releases_places_only_on_done(self):
        c=self.stub();c.card=None;c.sync_focus_menu=Mock();c.show_parked=Mock()
        c.toggle_focus();self.assertFalse(c.state['focused']);c.show_parked.assert_called_once()
        c.show_parked.reset_mock();c.toggle_focus();self.assertTrue(c.state['focused'])
        c.show_parked.assert_not_called();c.overlay_message.assert_called_with({'command':'dismiss_reply'})

    def test_step_away_phone_correction_focus_release_and_continue(self):
        from unittest.mock import patch
        import uuid
        c=self.stub();c.card=None;c.platform=Mock();c.platform.open_app.return_value=True
        c.state.update(snapshots=False,excluded_apps=[],outgoing=[],handled=[],allowed_apps=[
            {'id':str(uuid.uuid4()),'name':'Notes','bundle':'com.apple.Notes'}],reopen=True)
        c.acks=[];c.draft=Mock();c.sync_focus_menu=Mock();c.show_parked=Mock()
        c.hold_context({'app':'Notes','bundle':'com.apple.Notes','title':'Lecture notes'})
        identity=next(iter(c.state['places']))
        # The real phone reply is correlated to the saved idle Place.
        c.consume({'id':str(uuid.uuid4()),'kind':'place','payload':{
            'place_id':identity,'sentence':'Finish reviewing the lecture examples'}})
        c.overlay_message.assert_not_called()
        self.assertEqual(c.state['places'][identity]['sentence'],'Finish reviewing the lecture examples')
        c.toggle_focus();c.show_parked.assert_called_once()
        # Exercise the actual native Continue handler and local approval lookup.
        with patch('companion.threading.Thread') as thread:
            thread.side_effect=lambda target,args=(),**kw:Mock(start=lambda:target(*args))
            c.native_panel({'action':'place_action','id':identity,'choice':'continue'})
        c.platform.open_app.assert_called_once_with('com.apple.Notes')
        self.assertEqual(c.state['places'][identity]['status'],'finished')
