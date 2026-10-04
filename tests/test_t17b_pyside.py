import pytest
from sanguosha.ui.main_window import MainWindow
from sanguosha.engine.yj2011_tier3 import YJSkillAction
from sanguosha.engine.phases import PhaseAction
from sanguosha.engine.requests import RequestType
from sanguosha.model.enums import Phase
from test_t17b_tier1 import game,answer
from test_t17b_tier3 import active
from test_t6_military_basics import put


@pytest.mark.parametrize('general,skill',[('cao_zhi','jiushi_return'),('fa_zheng','enyuan_damage'),
    ('ma_su','xinzhan'),('wu_guotai','ganlu'),('chen_gong','mingce'),('gao_shun','xianzhen')])
def test_six_generals_pyside_load_descriptions_and_generic_requests(general,skill):
    s=game(); active(s,general); s.human_id='p1'; s.state.players['p1'].max_hp=3; s.state.players['p1'].hp=3
    put(s,'basic.slash')
    s.engine.start_action(YJSkillAction('qt-skill','p1',skill,'p2' if skill=='enyuan_damage' else None))
    w=MainWindow(); w.session=s; w._render()
    request=s.engine.pending_request
    if request.request_type is RequestType.CHOOSE_PLAYER:
        assert '选择目标' in w.decision.prompt_label.text()
        assert {pid for pid,panel in w.table.panels.items() if panel.targetable}==set(request.allowed_player_ids)
    else:
        assert request.prompt in w.decision.prompt_label.text()
    assert s.skills.characters['yj2011_'+general].name
    for sid in s.skills.characters['yj2011_'+general].skill_ids:
        assert s.skills.skills[sid].name in ' '.join(w.table.panels['p1'].view.skill_labels)
        assert len(s.skills.skills[sid].description)>12
    if s.engine.pending_request.request_type is RequestType.YES_NO:
        w._submit_value(False)
    w.close()
