from sanguosha.engine.rng import PythonRandomSource, RandomSource


def test_seeded_random_source_repeats_shuffle_and_choice() -> None:
    first: RandomSource = PythonRandomSource(42)
    second: RandomSource = PythonRandomSource(42)
    values_a = list(range(10))
    values_b = list(range(10))
    first.shuffle(values_a)
    second.shuffle(values_b)
    assert values_a == values_b
    assert first.choice(values_a) == second.choice(values_b)
