"""Exhaustive authoritative-roster reachability and metadata-driven Huashen filtering."""
from dataclasses import replace
from pathlib import Path
import json
import pytest
from test_t6_military_basics import game
from sanguosha.content.characters.standard import PLAYABLE_GENERAL_POOL, ORDINARY_GENERAL_POOL
from sanguosha.engine.mountain import draw_transformations, transformable_skills
from sanguosha.engine.skills import SkillRegistry
from sanguosha.model.enums import SkillType
from sanguosha.model.skill import SkillDefinition
from sanguosha.snapshot import snapshot_session, restore_session

BASE = tuple(c for c in ORDINARY_GENERAL_POOL if c.id != 'mountain_zuoci')
GODS = tuple(c for c in PLAYABLE_GENERAL_POOL if c not in ORDINARY_GENERAL_POOL)

class Pick:
    def __init__(self, expected): self.expected = expected
    def choice(self, candidates):
        assert self.expected in candidates
        return self.expected

def blank():
    s = game()
    s.state.players['p1'].character_id = 'mountain_zuoci'
    return s

@pytest.mark.parametrize('general', BASE, ids=lambda c:c.id)
def test_every_ordinary_general_is_drawable(general):
    s = blank()
    assert draw_transformations(s.state, 'p1', 1, SkillRegistry(), Pick(general.id)) == (general.id,)

@pytest.mark.parametrize('general', (*GODS, next(c for c in PLAYABLE_GENERAL_POOL if c.id=='mountain_zuoci')), ids=lambda c:c.id)
def test_gods_and_zuoci_never_enter_pool(general):
    s = blank()
    class Reject:
        def choice(self, candidates):
            assert general.id not in candidates
            return candidates[0]
    draw_transformations(s.state, 'p1', 1, SkillRegistry(), Reject())

@pytest.mark.parametrize('general', BASE, ids=lambda c:c.id)
def test_in_play_and_duplicate_forms_are_excluded_after_reconnect(general):
    s = blank()
    s.state.players['p2'].character_id = general.id
    s.state.players['p1'].transformation_pool = [BASE[(BASE.index(general)+1)%len(BASE)].id]
    s = restore_session(snapshot_session(s))
    excluded = {general.id, *s.state.players['p1'].transformation_pool}
    class Reject:
        def choice(self,candidates):
            assert excluded.isdisjoint(candidates)
            return candidates[0]
    draw_transformations(s.state,'p1',1,SkillRegistry(),Reject())

def test_pool_exactly_91_and_exhaustion_has_no_duplicates():
    assert len(BASE)==91 and len(GODS)==16
    s=blank()
    class First:
        def choice(self, candidates):return candidates[0]
    got=draw_transformations(s.state,'p1',999,SkillRegistry(),First())
    assert set(got)=={c.id for c in BASE} and len(got)==91
    assert draw_transformations(s.state,'p1',1,SkillRegistry(),First())==()

@pytest.mark.parametrize('kind', tuple(SkillType))
@pytest.mark.parametrize('flags', ({},{'lord':True},{'limited':True},{'awakening':True},{'transferable':False},{'hidden':True},{'hidden_skill':True},{'special':True},{'attached_lord':True}))
def test_filter_uses_type_and_metadata_for_new_skill_ids(kind,flags):
    registry=SkillRegistry()
    skill=SkillDefinition('future_skill','未来技能','仅用于通用过滤测试。',kind,flags)
    registry.skills[skill.id]=skill
    registry.characters['future_general']=replace(BASE[0],id='future_general',skill_ids=(skill.id,))
    expected=() if flags or kind in (SkillType.LIMITED,SkillType.AWAKENING) else (skill.id,)
    assert transformable_skills(registry,'future_general')==expected

@pytest.mark.parametrize('general', BASE, ids=lambda c:c.id)
def test_each_form_skill_obeys_classic_filter(general):
    registry=SkillRegistry()
    got=transformable_skills(registry,general.id)
    for sid in general.skill_ids:
        skill=registry.skills[sid]
        forbidden=(sid in general.metadata.get('derived_skills', ()) or skill.skill_type in (SkillType.LIMITED,SkillType.AWAKENING) or any(skill.metadata.get(k) for k in ('lord','limited','awakening','hidden','hidden_skill','special','attached_lord')) or skill.metadata.get('transferable') is False)
        assert (sid in got)==(not forbidden)

def test_huashen_death_clears_private_forms_and_active_skill_after_death_triggers():
    from test_t17c_first_batch import setup
    from sanguosha.engine.death import DeathAction
    from sanguosha.model.enums import Identity
    from sanguosha.engine.requests import Decision
    s=setup('cao_zhang')
    p=s.state.players['p1'];p.character_id='mountain_zuoci';p.identity=Identity.REBEL
    s.state.players['p2'].identity=Identity.LORD
    p.transformation_pool=['ganning'];p.active_transformation='ganning';p.transformation_skill='qixi'
    s.engine.start_action(DeathAction('zuoci-death','p1',None))
    while s.engine.pending_request:
        r=s.engine.pending_request;s.engine.submit_decision(Decision(r.request_id,r.player_id,r.timeout_value()))
    s=restore_session(snapshot_session(s));p=s.state.players['p1']
    assert not p.transformation_pool and p.active_transformation is None and p.transformation_skill is None

def test_new_registry_entry_and_renamed_god_need_no_pool_id_list():
    registry=SkillRegistry();s=blank()
    ordinary=replace(BASE[0],id='future_ordinary',metadata={'playable':True})
    god=replace(GODS[0],id='opaque_id',metadata={'playable':True,'god':True})
    registry.characters[ordinary.id]=ordinary;registry.characters[god.id]=god
    class Probe:
        def choice(self,candidates):
            assert 'future_ordinary' in candidates and 'opaque_id' not in candidates
            return 'future_ordinary'
    assert draw_transformations(s.state,'p1',1,registry,Probe())==('future_ordinary',)

def test_dead_in_play_general_still_excluded_and_pool_subtracts_exactly():
    from sanguosha.model.enums import PlayerStatus
    s=blank();registry=SkillRegistry()
    s.state.players['p2'].character_id=BASE[0].id
    s.state.players['p2'].status=PlayerStatus.DEAD
    s.state.players['p3'].character_id=BASE[1].id
    s.state.players['p1'].transformation_pool=[BASE[2].id]
    class First:
        def choice(self,candidates):return candidates[0]
    got=draw_transformations(s.state,'p1',999,registry,First())
    assert set(got)=={c.id for c in BASE}-{BASE[0].id,BASE[1].id,BASE[2].id}
    assert len(got)==88


def test_jiangwei_awakening_reward_is_not_a_native_huashen_choice():
    registry = SkillRegistry()
    assert transformable_skills(registry, 'mountain_jiang_wei') == ('tiaoxin',)
    assert 'guanxing' in transformable_skills(registry, 'zhugeliang')


def test_future_derived_skill_is_filtered_by_general_metadata():
    registry = SkillRegistry()
    skill = SkillDefinition('future_reward', 'Future reward', 'Granted after awakening.', SkillType.TRIGGERED)
    registry.skills[skill.id] = skill
    registry.characters['future_form'] = replace(BASE[0], id='future_form',
        skill_ids=(skill.id,), metadata={'derived_skills': (skill.id,)})
    assert transformable_skills(registry, 'future_form') == ()


def test_jiangwei_guanxing_requires_awakened_grant_and_survives_reconnect():
    from sanguosha.session import GameSession
    s = GameSession.new_game(military=True, five_generals=True)
    p = s.state.players['p1']
    p.character_id = 'mountain_jiang_wei'
    assert not s.skills.has(s.state, 'p1', 'guanxing')
    p.granted_skills['guanxing'] = 'zhiji'
    assert s.skills.has(s.state, 'p1', 'guanxing')
    restored = restore_session(snapshot_session(s))
    assert restored.skills.has(restored.state, 'p1', 'guanxing')


REVIEWED_SKILLS = json.loads((Path(__file__).resolve().parents[1] /
    'docs/t18a11/huashen_skill_eligibility.json').read_text(encoding='utf-8')) + json.loads((Path(__file__).resolve().parents[1] /
    'docs/t19/huashen_lusu_eligibility.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('row', REVIEWED_SKILLS,
    ids=lambda row: row['general_id'] + ':' + row['skill_id'])
def test_each_skill_matches_independently_reviewed_classic_eligibility(row):
    registry = SkillRegistry()
    assert (row['skill_id'] in transformable_skills(registry, row['general_id'])) is row['allowed']


def test_reviewed_eligibility_covers_every_current_form_skill():
    actual = {(c.id, sid) for c in BASE for sid in c.skill_ids}
    reviewed = {(r['general_id'], r['skill_id']) for r in REVIEWED_SKILLS}
    assert actual == reviewed
    assert len(REVIEWED_SKILLS) == len(reviewed)


@pytest.mark.parametrize('flags', ({'playable': False}, {'development_only': True}))
def test_nonformal_registry_entries_never_enter_pool(flags):
    registry = SkillRegistry()
    registry.characters['not_formal'] = replace(BASE[0], id='not_formal', metadata=flags)
    class Probe:
        def choice(self, candidates):
            assert 'not_formal' not in candidates
            return candidates[0]
    draw_transformations(blank().state, 'p1', 1, registry, Probe())


def test_form_without_gainable_skills_stays_in_general_pool():
    registry = SkillRegistry()
    registry.characters['future_empty_form'] = replace(BASE[0], id='future_empty_form', skill_ids=())
    assert draw_transformations(blank().state, 'p1', 1, registry,
        Pick('future_empty_form')) == ('future_empty_form',)


def test_another_zuoci_held_form_does_not_shrink_this_owners_pool():
    s = blank()
    s.state.players['p2'].transformation_pool = [BASE[0].id]
    assert draw_transformations(s.state, 'p1', 1, SkillRegistry(), Pick(BASE[0].id)) == (BASE[0].id,)


@pytest.mark.parametrize('row', [r for r in REVIEWED_SKILLS if r['allowed']],
    ids=lambda row: row['general_id'] + ':' + row['skill_id'])
def test_every_allowed_form_skill_is_acquired_through_request_after_reconnect(row):
    from sanguosha.session import GameSession
    from sanguosha.engine.mountain import HuashenAction
    from sanguosha.engine.requests import Decision
    from sanguosha.projection import project_for_human
    s = GameSession.new_game(military=True, five_generals=True, seed=13)
    p = s.state.players['p1']
    p.character_id = 'mountain_zuoci'
    p.transformation_pool = [row['general_id']]
    s.engine.start_action(HuashenAction('reviewed-huashen', 'p1'))
    request = s.engine.pending_request
    expected = {r['general_id'] + ':' + r['skill_id'] for r in REVIEWED_SKILLS
                if r['general_id'] == row['general_id'] and r['allowed']}
    assert set(request.choices) == expected
    opponent = project_for_human(s.state, s.definitions, 'p2', s.character_names)
    assert all(not view.transformation_pool for view in opponent.players)
    s = restore_session(snapshot_session(s))
    request = s.engine.pending_request
    assert set(request.choices) == expected
    choice = row['general_id'] + ':' + row['skill_id']
    s.engine.submit_decision(Decision(request.request_id, 'p1', choice))
    assert s.engine.pending_request is None
    assert s.skills.has(s.state, 'p1', row['skill_id'])
    form = s.skills.characters[row['general_id']]
    assert s.skills.faction(s.state, 'p1') == form.kingdom
    assert s.skills.gender(s.state, 'p1') == form.gender
    s = restore_session(snapshot_session(s))
    assert s.skills.has(s.state, 'p1', row['skill_id'])


@pytest.mark.parametrize('row', [r for r in REVIEWED_SKILLS if r['allowed']],
    ids=lambda row: row['general_id'] + ':' + row['skill_id'])
def test_each_gained_skill_switch_and_huashen_disable_revokes_only_its_permission(row):
    from sanguosha.session import GameSession
    from sanguosha.engine.mountain import HuashenAction
    from sanguosha.engine.requests import Decision
    s = GameSession.new_game(military=True, five_generals=True, seed=13)
    p = s.state.players['p1']; p.character_id = 'mountain_zuoci'
    p.transformation_pool = [row['general_id']]
    p.active_transformation = row['general_id']; p.transformation_skill = row['skill_id']
    assert s.skills.has(s.state, 'p1', row['skill_id'])
    p.disabled_skills.add('huashen')
    assert not s.skills.has(s.state, 'p1', row['skill_id'])
    p.disabled_skills.clear()
    alternate = 'ganning' if row['skill_id'] != 'qixi' else 'guanyu'
    next_skill = 'qixi' if alternate == 'ganning' else 'wusheng'
    if alternate not in p.transformation_pool: p.transformation_pool.append(alternate)
    s.engine.start_action(HuashenAction('switch-huashen', 'p1'))
    s = restore_session(snapshot_session(s));req = s.engine.pending_request
    s.engine.submit_decision(Decision(req.request_id, 'p1', alternate + ':' + next_skill))
    assert not s.skills.has(s.state, 'p1', row['skill_id'])
    assert s.skills.has(s.state, 'p1', next_skill)
    p = s.state.players['p1'];p.granted_skills[row['skill_id']] = 'independent-grant'
    assert s.skills.has(s.state, 'p1', row['skill_id'])
    # Huashen replacement must not erase another independent skill grant.
    s = restore_session(snapshot_session(s))
    assert s.skills.has(s.state, 'p1', row['skill_id'])


def test_huashen_timeout_fallback_selects_current_legal_choice_after_reconnect():
    from sanguosha.session import GameSession
    from sanguosha.engine.mountain import HuashenAction
    from sanguosha.engine.requests import Decision
    s = GameSession.new_game(military=True, five_generals=True)
    p = s.state.players['p1']; p.character_id = 'mountain_zuoci'
    p.transformation_pool = ['mountain_jiang_wei', 'yj2013_li_ru']
    s.engine.start_action(HuashenAction('timeout-huashen', 'p1'))
    s = restore_session(snapshot_session(s));req = s.engine.pending_request
    fallback = req.timeout_value();req.validate(fallback)
    s.engine.submit_decision(Decision(req.request_id, 'p1', fallback))
    general, skill = fallback.split(':')
    assert skill in transformable_skills(s.skills, general)
    assert s.skills.has(s.state, 'p1', skill)
