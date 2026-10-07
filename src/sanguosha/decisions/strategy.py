"""Compact public-information strategy, shared by the existing skill AIs."""
from functools import lru_cache
from sanguosha.content.characters.standard import ALL_GENERAL_POOL, ALL_SKILL_CATALOGUE
from sanguosha.model.enums import Identity
from sanguosha.model.zones import ZoneRef, ZoneType

GENERALS = {g.id: g for g in ALL_GENERAL_POOL}
SKILLS = {s.id: s for s in ALL_SKILL_CATALOGUE}
WORDS = {
    'damage': ('造成伤害', '造成一点', '伤害增加', '伤害加一'),
    'burst': ('不受次数限制', '杀上限加一', '不能响应', '额外回合', '伤害增加'),
    'draw': ('摸一张', '摸两张', '摸三张', '摸四张', '摸牌', '获得判定牌'),
    'control': ('取消目标', '跳过', '翻面', '转移目标', '减少一点体力上限'),
    'heal': ('回复', '恢复一点体力', '恢复体力'),
    'save': ('当桃', '濒死时', '濒死角色'),
    'protect': ('防止伤害', '不能成为', '取消此目标', '伤害无效'),
    'discard': ('弃置', '弃牌', '过河拆桥', '取得其他角色', '取走'),
    'give': ('交给', '交出', '分配', '令一名角色', '获得其全部场上牌'),
    'equip': ('装备区', '装备牌', '装备的牌'),
    'extra_turn': ('额外回合',),
}
# Exceptions describe skill intent, never individual general scripts.
SPECIAL = {
    'renjie': {'growth', 'draw'}, 'jilue': {'draw', 'control'},
    'lianpo': {'extra_turn', 'burst'}, 'shenzhu': {'draw', 'burst'},
    'lingce': {'draw'}, 'zhimeng': {'draw', 'give'}, 'dingzhou': {'control', 'equip'},
    'huishi': {'draw', 'give'}, 'fuhai': {'burst', 'draw'},
    'yiji': {'masochism', 'give', 'draw'}, 'fankui': {'masochism', 'discard'},
    'jieming': {'masochism', 'give', 'draw'}, 'fangzhu': {'masochism', 'control'},
    'ganglie': {'masochism', 'damage'}, 'jianxiong': {'masochism', 'draw'},
}

@lru_cache(None)
def skill_tags(sid):
    skill = SKILLS.get(sid)
    if not skill: return frozenset()
    tags = set(skill.metadata.get('tags', ())) | SPECIAL.get(sid, set())
    for tag, words in WORDS.items():
        if any(w in skill.description for w in words): tags.add(tag)
    if skill.skill_type.value == 'view_as': tags.add('view_as')
    if skill.skill_type.value == 'awakening' or skill.metadata.get('awakening'): tags.add('awakening')
    if skill.metadata.get('limited') or skill.skill_type.value == 'limited': tags.add('limited')
    return frozenset(tags)

def active_skills(state, pid):
    p = state.players[pid]; g = GENERALS.get(p.character_id)
    ids = set(g.skill_ids if g else ()) - set(g.metadata.get('derived_skills', ()) if g else ())
    ids.update(p.granted_skills)
    if p.transformation_skill: ids.add(p.transformation_skill)
    if p.marks.get('wuwei'): ids.add('wushuang')
    from sanguosha.engine.skill_leases import suppressed
    return {sid for sid in ids if sid not in p.disabled_skills and not suppressed(state,pid,sid)}

def profile(state, pid):
    return set().union(*(skill_tags(sid) for sid in active_skills(state,pid)))

def hand_count(state, pid):
    return len(state.cards_in(ZoneRef(ZoneType.HAND,pid)))

def threat(state, pid):
    p=state.players[pid]; tags=profile(state,pid)
    weights={'damage':8,'burst':14,'draw':12,'control':12,'heal':5,'save':10,
             'protect':5,'discard':8,'give':7,'view_as':4,'extra_turn':16}
    score=sum(weight for tag,weight in weights.items() if tag in tags)
    if 'limited' in tags and any(not p.marks.get(sid+'_used') for sid in active_skills(state,pid) if 'limited' in skill_tags(sid)):
        score+=10
    if 'awakening' in tags:
        if p.marks.get('ren',0)>=3 or p.hp<=2 or any(len(z.card_ids)>=3 for ref,z in state.zones.items() if ref.player_id==pid and ref.zone_type is ZoneType.SPECIAL): score+=12
    if p.marks.get('ren'): score+=min(8,p.marks['ren']*2)
    return score if p.face_up else score*.6

def strength(state,pid):
    p=state.players[pid]
    equipment=sum(len(z.card_ids) for ref,z in state.zones.items() if ref.player_id==pid and ref.zone_type is ZoneType.EQUIPMENT)
    return max(0,p.hp)*3+hand_count(state,pid)*1.3+equipment*2+threat(state,pid)*.15

def lord_id(state):
    return next((pid for pid in state.revealed_identities if state.players[pid].identity is Identity.LORD),None)

def belief(state,pid):
    """Positive means supportive of the lord; inferred solely from public acts."""
    lord=lord_id(state); ledger=state.metadata.get('public_attitude',{})
    direct=ledger.get(str(pid),{}).get(str(lord),0)
    score=direct
    for target,value in ledger.get(str(pid),{}).items():
        if target==lord: continue
        known=ledger.get(str(target),{}).get(str(lord),0)
        if abs(known)>=2: score+=value*(1 if known>0 else -1)*.35
    return max(-8,min(8,score))

def exposure_cost(ai,state,actor,target,damage=1):
    from sanguosha.game_modes import game_mode
    if game_mode(state.metadata.get('mode_id','military-five')).public_sides: return 0
    if state.players[actor].identity is not Identity.REBEL or target!=lord_id(state): return 0
    if state.players[target].hp<=damage: return 0
    if state.turn_number>len(state.seat_order)*2 or belief(state,actor)<=-2: return 0
    # A safe lord, a weak attack and no prepared burst do not justify jumping out.
    slashes=sum('slash' in state.cards[c].definition_id for c in state.cards_in(ZoneRef(ZoneType.HAND,actor)))
    return 100 if state.players[target].hp>=3 and not ('burst' in profile(state,actor) and slashes>=2) else 20

def support_score(ai,state,actor,target):
    p=state.players[target]; tags=profile(state,target)
    return -ai._priority(state,actor,target)+threat(state,target)*.4+(p.max_hp-p.hp)*5+('burst' in tags)*8-hand_count(state,target)*2

def damage_terms(ai,state,actor,target,damage=1,elemental=False):
    p=state.players[target]; tags=profile(state,target); own=profile(state,actor)
    hostile=ai._priority(state,actor,target)>0
    terms={'relation':ai._priority(state,actor,target)*.6,
           'high_threat':threat(state,target)*.4 if hostile else -threat(state,target)*.2,
           'defense':-min(hand_count(state,target),6)*3-('protect' in tags)*8,
           'kill':90 if hostile and p.hp<=damage else -90 if not hostile and p.hp<=damage else 0,
           'masochism':-28 if hostile and 'masochism' in tags and p.hp>damage else 0,
           'identity_exposure':-exposure_cost(ai,state,actor,target,damage)}
    if hostile and p.hp<=damage:
        savers=[q for q in state.seat_order if q!=target and state.players[q].is_alive and
                'save' in profile(state,q) and hand_count(state,q)>0 and ai._priority(state,actor,q)>0]
        terms['rescue_risk']=-min(20,len(savers)*10)
    if 'masochism' in tags and 'control' in own: terms['masochism']-=4
    if elemental and p.chained:
        terms['chain']=sum((12 if ai._priority(state,actor,q)>0 else -22)*(2 if state.players[q].hp<=damage else 1)
                           for q in state.seat_order if q!=target and state.players[q].is_alive and state.players[q].chained)
    return terms

def learning_score(ai,state,pid,choice):
    hand=state.cards_in(ZoneRef(ZoneType.HAND,pid)); p=state.players[pid]
    enemies=[q for q in state.seat_order if q!=pid and state.players[q].is_alive and ai._priority(state,pid,q)>0]
    kill=any(state.players[q].hp<=1 for q in enemies)
    attacks=sum('slash' in state.cards[c].definition_id for c in hand)
    tricks=sum(state.cards[c].definition_id.startswith('trick.') for c in hand)
    scores={'learn:wansha':100 if kill and attacks else 28,
            'learn:jizhi':42+tricks*12,'learn:zhiheng':40+max(0,len(hand)-2)*7,
            'learn:fangzhu':65 if p.hp<=2 else 32,'learn:guicai':62 if any(z.card_ids for ref,z in state.zones.items() if ref.zone_type is ZoneType.JUDGMENT) else 24,
            'extra_turn':48+attacks*15+tricks*5+(25 if kill else 0),
            'draw:2':38 if len(hand)<=1 else 18,'draw:1':22 if len(hand)<=1 else 8,'cancel':0}
    return scores.get(choice,0)
