"""Oráculo exaustivo pequeno para a otimização e ambiguidade globais."""

from itertools import product
from random import Random

import pytest

from comprova_lattes.matcher import MatcherConfig, MatcherThresholds
from comprova_lattes.matcher.association import _optimal, associate


def exhaustive(scores, threshold):
    rows, columns = len(scores), len(scores[0])
    valid = []
    for assignment in product([None, *range(columns)], repeat=rows):
        used = [j for j in assignment if j is not None]
        if len(set(used)) != len(used):
            continue
        if any(j is not None and scores[i][j] < threshold for i, j in enumerate(assignment)):
            continue
        total = sum(scores[i][j] for i, j in enumerate(assignment) if j is not None)
        valid.append((total, assignment))
    return valid


@pytest.mark.parametrize("rows,columns", [(1, 3), (3, 1), (2, 3), (3, 2), (3, 3), (3, 0)])
def test_global_solver_against_exhaustive_oracle(rows, columns):
    rng = Random(17)
    config = MatcherConfig(
        thresholds=MatcherThresholds(
            association=0.5,
            ambiguity_margin=0.02,
            holder_low=0.4,
            holder_high=0.9,
            title_low=0.4,
            title_high=0.9,
            institution_low=0.4,
            institution_high=0.9,
        )
    )
    for _ in range(12):
        scores = [
            [rng.choice([0.0, 0.49, 0.5, 0.8, 0.81, 1.0]) for _ in range(columns)]
            for _ in range(rows)
        ]
        valid = exhaustive(scores, 0.5)
        best = max(total for total, _ in valid)
        total, chosen = _optimal(scores, 0.5)
        assert total == pytest.approx(best)
        assert any(chosen == list(assignment) for _, assignment in valid)
        _, ambiguous = associate(scores, config)
        nearby = [assignment for total, assignment in valid if best - total <= 0.02 + 1e-12]
        expected = {}
        for i in range(rows):
            candidates = {assignment[i] for assignment in nearby}
            if len(candidates) > 1:
                expected[i] = candidates - {None}
        assert {i: set(candidates) for i, candidates in ambiguous.items()} == expected
