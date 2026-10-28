"""5.6 NSGA-II: ordenação não dominada, multidão, operadores e convergência num problema conhecido."""

import random

from tcc_frota.algoritmos import nsga2 as ng


def test_nondominated_sort_and_crowding():
    objs = [(1, 4), (2, 2), (4, 1), (3, 3), (5, 5)]
    fronts = ng.nondominated_sort(objs)
    assert sorted(fronts[0]) == [0, 1, 2] and fronts[1] == [3] and fronts[2] == [4]
    cd = ng.crowding(objs, fronts[0])
    assert cd[0] == cd[2] == float("inf") and 0 < cd[1] < float("inf")


def test_operators_stay_in_bounds_and_decode():
    rng = random.Random(1)
    for _ in range(200):
        a = [rng.uniform(lo, hi) for lo, hi in ng.BOUNDS]
        b = [rng.uniform(lo, hi) for lo, hi in ng.BOUNDS]
        for c in (*ng.sbx(a, b, rng), ng.mutate(a, rng)):
            assert all(lo <= v <= hi for v, (lo, hi) in zip(c, ng.BOUNDS))
            p = ng.decode(c)
            assert p["teto"] is None or 1 <= p["teto"] <= 5
    assert ng.decode([0.5, 1.0, 3.0, 5.99999, 0.0])["teto"] == 5


def test_nsga2_approaches_known_front():
    # min (x0, 1 - x0 + soma dos demais): fronteira com os demais genes no limite inferior
    def ev(x):
        g = sum((v - lo) / (hi - lo) for v, (lo, hi) in zip(x[1:], ng.BOUNDS[1:]))
        f0 = (x[0] - ng.BOUNDS[0][0]) / (ng.BOUNDS[0][1] - ng.BOUNDS[0][0])
        return (f0, 1 - f0 + g), {}

    hist = ng.nsga2(ev, random.Random(3), pop_size=20, generations=30)
    assert len(hist) == 600
    best_g = min(o[0] + o[1] - 1 for _, o, _ in hist)
    assert best_g < 0.2
