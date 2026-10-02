"""Skill loss stays authoritative across UI projection and reconnection."""

from sanguosha.projection import project_for_human
from sanguosha.session import GameSession
from sanguosha.snapshot import restore_session, snapshot_session


def test_disabled_skill_is_not_available_and_survives_reconnect():
    session = GameSession.new_game(military=True, five_generals=True)
    player = session.state.players['p1']
    player.character_id = 'caocao'
    assert session.skills.has(session.state, 'p1', 'jianxiong')
    player.disabled_skills.add('jianxiong')
    assert not session.skills.has(session.state, 'p1', 'jianxiong')

    view = project_for_human(session.state, session.definitions, 'p1', session.character_names)
    assert any('奸雄' in label and '已失去' in label for label in view.players[0].skill_labels)

    restored = restore_session(snapshot_session(session))
    assert 'jianxiong' in restored.state.players['p1'].disabled_skills
    assert not restored.skills.has(restored.state, 'p1', 'jianxiong')
