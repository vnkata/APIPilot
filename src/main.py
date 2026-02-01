from hypothesis import given, strategies as st


def mean(xs: list[int]) -> float:
    return sum(xs) / len(xs)


@given(st.lists(st.integers(), min_size=1, max_size=10))
def test_sum_of_integers(int_list):
    total = sum(int_list)
    assert total >= min(int_list)
    assert total <= max(int_list) * len(int_list)


@given(st.lists(st.integers()))
def test_mean_never_crashes(xs):
    mean(xs)
