"""Injectable source for all future game randomness."""

import random
from typing import MutableSequence, Protocol, Sequence, TypeVar

T = TypeVar("T")


class RandomSource(Protocol):
    def shuffle(self, values: MutableSequence[T]) -> None: ...

    def choice(self, values: Sequence[T]) -> T: ...


class PythonRandomSource:
    def __init__(self, seed: int | str | bytes | None = None) -> None:
        self._random = random.Random(seed)

    def shuffle(self, values: MutableSequence[T]) -> None:
        self._random.shuffle(values)

    def choice(self, values: Sequence[T]) -> T:
        return self._random.choice(values)
