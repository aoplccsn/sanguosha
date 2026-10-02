"""A view-as value references physical costs without creating a CardInstance."""
from dataclasses import dataclass
from .enums import Suit,Color

@dataclass(frozen=True,slots=True)
class VirtualCard:
    definition_id: str
    material_ids: tuple[str,...]
    suit: Suit | None
    color: Color | None

    @classmethod
    def spear(cls,state,materials,suit_resolver=None):
        cards=tuple(state.cards[cid] for cid in materials)
        interpreted=tuple(suit_resolver(state,cid) if suit_resolver else c.suit
                          for cid,c in zip(materials,cards))
        suits=set(interpreted)
        colors={Color.RED if suit in (Suit.HEART,Suit.DIAMOND) else Color.BLACK
                for suit in interpreted}
        return cls('basic.slash',tuple(materials),next(iter(suits)) if len(suits)==1 else None,
                   next(iter(colors)) if len(colors)==1 else None)
