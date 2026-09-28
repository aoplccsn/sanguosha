"""Fixed physical prints remain complete and registered."""

from collections import Counter

from sanguosha.content.cards.basic import register_basic_cards
from sanguosha.content.cards.classic_military import register_additional_definitions
from sanguosha.engine.card_registry import CardDefinitionRegistry
from sanguosha.engine.card_rules import CardRuleRegistry
from sanguosha.engine.deck import classic_military_deck
from sanguosha.engine.rng import PythonRandomSource
from sanguosha.model.zones import ZoneType


def test_classic_military_deck_manifest():
    cards, zone = classic_military_deck(PythonRandomSource(3))
    definitions = CardDefinitionRegistry()
    register_basic_cards(definitions, CardRuleRegistry())
    register_additional_definitions(definitions)
    assert len(cards) == len(zone.card_ids) == 160
    assert len(set(zone.card_ids)) == 160
    assert zone.ref.zone_type is ZoneType.DRAW_PILE
    assert all(definitions.get(card.definition_id) for card in cards.values())
    assert len({card.definition_id for card in cards.values()}) == 43
    assert all(1 <= card.rank <= 13 for card in cards.values())
    counts = Counter(card.definition_id for card in cards.values())
    expected = {
        'basic.slash': 30, 'basic.fire_slash': 5, 'basic.thunder_slash': 9,
        'basic.dodge': 24, 'basic.peach': 12, 'basic.wine': 5,
        'trick.dismantlement': 6, 'trick.snatch': 5, 'trick.ex_nihilo': 4,
        'trick.duel': 3, 'trick.savage_assault': 3, 'trick.archery_attack': 1,
        'trick.god_salvation': 1, 'trick.amazing_grace': 2,
        'trick.borrowed_sword': 2, 'trick.nullification': 7,
        'trick.fire_attack': 3, 'trick.iron_chain': 6,
        'delayed.indulgence': 3, 'delayed.lightning': 2,
        'delayed.supply_shortage': 2,
        'equipment.weapon.crossbow': 2,
        'equipment.armor.eight_trigrams': 2, 'equipment.armor.vine': 2,
    }
    singletons = (
        'double_sword', 'qinggang_sword', 'green_dragon_blade', 'serpent_spear',
        'rock_cleaving_axe', 'halberd', 'kylin_bow', 'ice_sword', 'ancient_blade',
        'vermilion_fan',
    )
    expected.update({f'equipment.weapon.{key}': 1 for key in singletons})
    expected.update({f'equipment.armor.{key}': 1 for key in ('renwang_shield', 'silver_lion')})
    expected.update({f'equipment.horse.{key}': 1 for key in (
        'jueying', 'zhaohuangfeidian', 'dilu', 'hualiu', 'chitu', 'dayuan', 'zixing',
    )})
    assert counts == expected
    for set_name, expected_multiplicity in (('std', 2), ('mil', 1)):
        for suit in ('spade', 'heart', 'club', 'diamond'):
            for rank in range(1, 14):
                assert len([card_id for card_id in cards
                            if str(card_id).startswith(f'{set_name}-{suit}-{rank:02d}')]) == expected_multiplicity
