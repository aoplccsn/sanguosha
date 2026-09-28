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
    def spear(cls,state,materials):
        cards=tuple(state.cards[cid] for cid in materials)
        suits={c.suit for c in cards}
        colors={c.color for c in cards}
        return cls('basic.slash',tuple(materials),next(iter(suits)) if len(suits)==1 else None,
                   next(iter(colors)) if len(colors)==1 else None)
