"""Required T19 sampling checks; skill-dependent integration waits for rules lock."""
import pytest
from sanguosha.general_draft import draft_general_ids, OVERPOWERED_WEIGHTS
from sanguosha.engine.rng import PythonRandomSource

ORDINARY = tuple(f'ordinary_{i}' for i in range(20)) + ('mobile_god_lusu',)
CATALOGUE = ORDINARY + tuple(OVERPOWERED_WEIGHTS)

class Tickets:
    def __init__(self, *tickets): self.tickets = iter(tickets)
    def choice(self, values):
        ticket = next(self.tickets)
        assert ticket in values
        return ticket
    def shuffle(self, values): pass

@pytest.mark.parametrize('slot,expected', [(499, 1), (500, 0)])
def test_slot_rate_boundary(slot, expected):
    offer = draft_general_ids(CATALOGUE, (), Tickets(slot, 0))
    assert len(offer) == 10
    assert sum(gid in OVERPOWERED_WEIGHTS for gid in offer) == expected

@pytest.mark.parametrize('ticket,expected', [
    (0, 'mobile_god_taishici'), (9, 'mobile_god_taishici'),
    (10, 'mobile_god_sunce'), (17, 'mobile_god_sunce'),
    (18, 'mountain_god_simayi'), (24, 'mountain_god_simayi'),
    (25, 'mobile_god_guojia'), (30, 'mobile_god_guojia'),
    (31, 'mobile_god_xunyu'), (34, 'mobile_god_xunyu'),
])
def test_weight_boundaries(ticket, expected):
    assert draft_general_ids(CATALOGUE, (), Tickets(0, ticket))[-1] == expected

def test_seeded_offers_exclude_taken_and_duplicates():
    taken = ('mobile_god_taishici', 'ordinary_0')
    left, right = PythonRandomSource(19), PythonRandomSource(19)
    for _ in range(100):
        offer = draft_general_ids(CATALOGUE + CATALOGUE, taken, left)
        assert offer == draft_general_ids(CATALOGUE + CATALOGUE, taken, right)
        assert len(set(offer)) == len(offer) == 10
        assert not set(offer).intersection(taken)
        assert sum(gid in OVERPOWERED_WEIGHTS for gid in offer) <= 1

def test_lusu_stays_ordinary_and_no_powered_falls_back():
    offer = draft_general_ids(('mobile_god_lusu',) + ORDINARY, (), Tickets(0))
    assert offer[0] == 'mobile_god_lusu'
    assert len(offer) == 10
