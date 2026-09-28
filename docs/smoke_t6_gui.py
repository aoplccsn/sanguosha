"""Offscreen military GUI full games, with the human Decision UI driven by AI."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ['SANGUOSHA_FAST_AI']='1'
import json
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication,QEvent
from sanguosha.ui.main_window import MainWindow
from sanguosha.session import GameSession
from sanguosha.engine.requests import RequestType
from sanguosha.model.state import GameStatus
from sanguosha.model.zones import ZoneRef,ZoneType

def match(seed):
    w=MainWindow(); w.show()
    w.session=GameSession.new_game(seed,military=True)
    s=w.session
    w._render()
    steps=0
    while s.state.status is not GameStatus.FINISHED and steps<20000:
        r=s.engine.pending_request
        if r and r.player_id==s.human_id:
            decision=s.ai.decide(s.state,r)
            value=decision.value
            if r.request_type is RequestType.CHOOSE_OPTION and isinstance(value,str) and value.startswith('use:'):
                cid=value[4:]; w._card_clicked(cid)
                rule=s.engine.registry.handler_for(__import__('sanguosha.engine.card_use',fromlist=['UseCardAction']).UseCardAction('preview',s.human_id,cid)).validator.rule_for(s.state,cid)
                if rule.requires_target_selection:
                    choices=rule.target_candidates(s.state,s.human_id)
                    low,high=rule.target_bounds(s.state,s.human_id,cid) if hasattr(rule,'target_bounds') else (1,1)
                    selected=choices[:low] if high>1 else (max(choices,key=lambda p:s.ai._priority(s.state,s.human_id,p)),)
                    for pid in selected: w._player_clicked(pid)
                w._submit_value('ui.confirm_play')
            elif r.request_type is RequestType.CHOOSE_PLAYER:
                w._player_clicked(value); w._submit_value('ui.confirm_target')
            elif r.request_type is RequestType.CHOOSE_PLAYERS:
                for pid in value: w._player_clicked(pid)
                w._submit_value(tuple(pid for pid in r.allowed_player_ids if str(pid) in w._selected_players))
            elif r.request_type is RequestType.RESPOND_WITH_CARD and isinstance(value,str) and value in s.state.cards:
                w._card_clicked(value); w._submit_value('ui.confirm_response')
            else:
                w._submit_value(value)
        else:
            s.step_auto(); w._render()
        w._tick_timer.stop(); w._tick_scheduled=False
        s.state.__post_init__(); steps+=1
        if steps%40==0: assert not w.grab().isNull()
    assert s.state.status is GameStatus.FINISHED,(seed,steps,w.decision.prompt_label.text())
    assert s.engine.pending_request is None and s.engine.stack.is_empty()
    assert not s.state.cards_in(ZoneRef(ZoneType.PROCESSING))
    assert len(s.state.cards)==160
    result={'seed':seed,'steps':steps,'turns':s.state.turn_number,'winner':s.state.victory.label,'gui':'PASS'}
    w.close(); w.deleteLater(); QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete); QApplication.processEvents()
    return result

if __name__=='__main__':
    app=QApplication.instance() or QApplication([])
    for seed in range(1,6):
        print(json.dumps(match(seed),ensure_ascii=False),flush=True)
