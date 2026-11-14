"""Atribuição global de soma máxima com alternativas dentro da margem configurada.

O algoritmo húngaro inclui colunas fictícias (sem documento). Para cada
aresta elegível, uma nova solução forçada identifica alternativas globais;
assim empates e disputas não dependem da ordem dos registros de entrada.
"""

from .models import FieldEvidence, MatcherConfig
from .text import normalize_text


def association_score(fields: list[FieldEvidence]) -> float:
    """Média não ponderada dos atributos de identidade presentes nos dois lados.

    Exige título ou evento comparável. Carga e papel ficam fora da afinidade:
    não bloqueiam associação necessária para detectar mutação ou falta de prova.
    Ausências não ganham pontos; nenhuma confiança do extrator é consultada.
    """
    comparable = [
        field
        for field in fields
        if field.field_name
        in {
            "titular",
            "titulo",
            "evento",
            "instituicao",
            "ano",
        }
        and field.lattes_raw is not None
        and field.document_raw is not None
        and normalize_text(str(field.lattes_raw)) is not None
        and normalize_text(str(field.document_raw)) is not None
    ]
    anchors = [f for f in comparable if f.field_name in {"titulo", "evento"}]
    if not anchors:
        return 0.0
    scores = [
        f.similarity_score if f.similarity_score is not None else float(f.outcome == "MATCH")
        for f in comparable
    ]
    return sum(scores) / len(scores) if scores else 0.0


def _optimal(
    scores: list[list[float]], threshold: float, forced: tuple[int, int | None] | None = None
) -> tuple[float, list[int | None]]:
    """Húngaro retangular O(n²(m+n)), sem dependências numéricas."""
    n = len(scores)
    if not n:
        return 0.0, []
    m = len(scores[0])
    width = m + n
    costs = []
    for i, row in enumerate(scores):
        values = [-s if s >= threshold else 1e6 for s in row] + [0.0] * n
        if forced and i == forced[0]:
            selected = forced[1] if forced[1] is not None else m + i
            values = [cost if j == selected else 1e6 for j, cost in enumerate(values)]
        costs.append(values)
    u, v = [0.0] * (n + 1), [0.0] * (width + 1)
    owners, paths = [0] * (width + 1), [0] * (width + 1)
    for i in range(1, n + 1):
        owners[0], column = i, 0
        minimum, used = [float("inf")] * (width + 1), set()
        while True:
            used.add(column)
            row, delta, next_column = owners[column], float("inf"), 0
            for j in range(1, width + 1):
                if j in used:
                    continue
                reduced = costs[row - 1][j - 1] - u[row] - v[j]
                if reduced < minimum[j]:
                    minimum[j], paths[j] = reduced, column
                if minimum[j] < delta:
                    delta, next_column = minimum[j], j
            for j in range(width + 1):
                if j in used:
                    u[owners[j]] += delta
                    v[j] -= delta
                else:
                    minimum[j] -= delta
            column = next_column
            if owners[column] == 0:
                break
        while column:
            previous = paths[column]
            owners[column] = owners[previous]
            column = previous
    assignment = [None] * n
    for j in range(1, m + 1):
        if owners[j]:
            assignment[owners[j] - 1] = j - 1
    total = sum(scores[i][j] for i, j in enumerate(assignment) if j is not None)
    return total, assignment


def associate(
    scores: list[list[float]], config: MatcherConfig
) -> tuple[list[int | None], dict[int, list[int]]]:
    threshold = config.thresholds.association
    optimum, chosen = _optimal(scores, threshold)
    ambiguous = {}
    for i, row in enumerate(scores):
        alternatives = []
        for j in [None, *(j for j, score in enumerate(row) if score >= threshold)]:
            total, _ = _optimal(scores, threshold, (i, j))
            if optimum - total <= config.thresholds.ambiguity_margin + 1e-12:
                alternatives.append(j)
        if len(alternatives) > 1:
            ambiguous[i] = [j for j in alternatives if j is not None]
    return chosen, ambiguous
