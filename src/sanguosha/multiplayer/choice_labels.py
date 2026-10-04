"""Viewer-safe Chinese labels; wire values remain machine-readable."""

from sanguosha.content.characters.standard import ALL_GENERAL_POOL, ALL_SKILL_CATALOGUE
from sanguosha.model.zones import ZoneType

GENERAL_NAMES = {str(item.id): item.name for item in ALL_GENERAL_POOL}
SKILL_NAMES = {str(item.id): item.name for item in ALL_SKILL_CATALOGUE}
CHOICE_NAMES = {
    'end_play_phase': '结束出牌', 'draw': '摸牌', 'discard': '弃牌',
    'draw_then_discard': '先摸牌，再弃牌', 'discard_then_draw': '先弃牌，再摸牌',
    'draw_x_discard_one': '摸 X 张，弃一张', 'draw_one_discard_x': '摸一张，弃 X 张',
    'lose_hp': '失去体力', 'lose_max_hp': '减体力上限', 'rage': '弃一枚怒标记',
    'give': '交出一张手牌', 'use_slash': '视为使用杀',
    'slash': '打出杀', 'damage': '造成伤害', 'recover': '回复体力',
    'top': '置于牌堆顶', 'bottom': '置于牌堆底', 'random_hand': '随机获得一张手牌',
    'decline': '放弃', 'done': '完成', 'yes': '是', 'no': '否',
    'small': '小业炎', 'great': '大业炎', 'wind': '狂风', 'fog': '大雾',
    'hp': '失去一点体力', 'weapon': '弃置武器',
    'spade': '黑桃', 'heart': '红桃', 'club': '梅花', 'diamond': '方块',
}


def choice_labels(room, request):
    session = room.session
    def card_name(card_id):
        if session is None or card_id not in session.state.cards:
            return None
        # Only reveal own/private or already public cards. An opponent hand stays hidden.
        ref = next((ref for ref, zone in session.state.zones.items()
                    if card_id in zone.card_ids), None)
        if ref is None:
            return None
        if ref.zone_type in (ZoneType.HAND, ZoneType.SPECIAL) and ref.player_id != request.player_id:
            return '背面手牌' if ref.zone_type is ZoneType.HAND else '特殊区牌'
        if ref.zone_type is ZoneType.DRAW_PILE:
            return '背面牌'
        card = session.state.cards[card_id]
        definition = session.definitions.get(card.definition_id)
        suit = CHOICE_NAMES.get(str(card.suit), '')
        return f'{definition.name}（{suit}{card.rank}）'

    def label(value, index):
        if value in CHOICE_NAMES:
            return CHOICE_NAMES[value]
        if value in GENERAL_NAMES:
            return GENERAL_NAMES[value]
        if value in SKILL_NAMES:
            return SKILL_NAMES[value]
        if value in room.seats:
            name = room.seats[value].name
            return name or '该角色'
        name = card_name(value)
        if name:
            return name
        prefix, _, suffix = value.partition(':')
        if prefix in GENERAL_NAMES and suffix in SKILL_NAMES:
            return f'{GENERAL_NAMES[prefix]} · {SKILL_NAMES[suffix]}'
        if prefix in ('top', 'bottom', 'better'):
            return f'{CHOICE_NAMES.get(prefix, "改判为")} · {card_name(suffix) or "所选牌"}'
        if prefix in ('equipment', 'area'):
            return card_name(suffix) or '区域牌'
        if prefix == 'hand':
            return f'背面手牌 {int(suffix) + 1}' if suffix.isdigit() else '背面手牌'
        if prefix == 'damage':
            return f'受到 {suffix} 点伤害' if suffix.isdigit() else '受到伤害'
        if prefix == 'current':
            return '保留当前判定'
        if prefix in ('skill', 'virtual'):
            skill_id = suffix.partition(':')[0]
            return SKILL_NAMES.get(skill_id, '丈八蛇矛' if skill_id == 'spear' else '技能选项')
        if session is not None:
            try:
                return session.definitions.get(value).name
            except Exception:
                pass
        return f'选项 {index + 1}'
    values = tuple(dict.fromkeys((*request.choices,
                  *(value for value in request.eligible_card_ids if value.startswith('virtual:')))))
    return {value: label(value, index) for index, value in enumerate(values)}
