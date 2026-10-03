from types import SimpleNamespace

from sanguosha.engine.requests import PendingRequest, RequestType
from sanguosha.multiplayer.choice_labels import choice_labels, CHOICE_NAMES
from sanguosha.multiplayer.room import MultiplayerRoom
from sanguosha.content.characters.standard import ALL_SKILL_CATALOGUE
from test_t6_military_basics import game, put


def request(choices):
    return PendingRequest('labels', 'p1', RequestType.CHOOSE_OPTION,
                          '选择', 'action', 'frame', choices=tuple(choices))


def test_every_fixed_branch_is_chinese():
    room = MultiplayerRoom()
    labels = choice_labels(room, request(CHOICE_NAMES))
    assert all(any('\u3400' <= char <= '\u9fff' for char in value) for value in labels.values())
    assert all(any('\u3400' <= char <= '\u9fff' for char in skill.name)
               for skill in ALL_SKILL_CATALOGUE)


def test_huashen_and_view_as_use_catalogue_names():
    room = MultiplayerRoom()
    values = ['wind_wei_yan:kuanggu', 'virtual:kanpo:black-card', 'small', 'great', 'wind', 'fog']
    labels = choice_labels(room, request(values))
    assert labels[values[0]] == '魏延 · 狂骨'
    assert labels[values[1]] == '看破'
    assert labels['great'] == '大业炎'


def test_choice_labels_never_reveal_an_opponent_hand():
    room = MultiplayerRoom()
    room.session = game()
    secret_card = put(room.session, 'trick.nullification', 'p2')
    labels = choice_labels(room, request([secret_card]))
    assert labels[secret_card] == '背面手牌'
    assert '无懈可击' not in str(labels)
