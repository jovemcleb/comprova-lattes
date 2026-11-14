"""Calibração exclusivamente piloto e manifesto verificável por SHA-256."""

import hashlib
import json
from collections.abc import Mapping, Sequence

from comprova_lattes.matcher.models import MatcherConfig

from .runner import evaluate
from .synthetic import Case, Corpus


def canonical(value) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False
    ).encode()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def calibrate(cases: Sequence[Case], candidates: Sequence[MatcherConfig]) -> dict:
    if not cases or any(c.partition != "pilot" for c in cases) or not candidates:
        raise ValueError("Calibração exige apenas piloto e candidatos explícitos")
    gold = {c.case_id: c.gold for c in cases if c.gold}
    scores = [evaluate(cases, gold, cfg)["macro_f1"] for cfg in candidates]
    best = max(range(len(scores)), key=lambda i: (scores[i], -i))
    return {
        "config": candidates[best].model_dump(mode="json"),
        "scores": scores,
        "selected": best,
        "pilot_ids": [c.case_id for c in cases],
        "objective": "macro_f1; first tie wins",
        "pilot_sha256": sha256(canonical([case_digest(c) for c in cases])),
    }


def case_digest(case: Case) -> dict:
    return {
        "id": case.case_id,
        "family": case.family_id,
        "partition": case.partition,
        "template": case.template_id,
        "issuer": case.issuer_id,
        "xml": sha256(case.xml),
        "curriculum": case.curriculum.model_dump(mode="json"),
        "operator": case.operator,
        "degradation": case.degradation,
        "mime_type": case.mime_type,
        "document": sha256(case.document) if case.document else None,
        "truth": case.expected,
        "gold": case.gold.model_dump(mode="json") if case.gold else None,
    }


def freeze(corpus: Corpus, calibration: dict, artifacts: Mapping[str, bytes]) -> dict:
    required = {
        "schema",
        "prompt",
        "regex",
        "acronyms",
        "normalization",
        "generator",
        "code",
        "environment",
    }
    if not required <= artifacts.keys() or any(not v for v in artifacts.values()):
        raise ValueError(f"Artefatos obrigatórios: {sorted(required)}")
    pilot = corpus.select("pilot")
    if calibration["pilot_sha256"] != sha256(canonical([case_digest(c) for c in pilot])):
        raise ValueError("Piloto diverge da calibração")
    payload = {
        "version": 1,
        "seed": corpus.seed,
        "calibration": calibration,
        "artifacts": {k: sha256(v) for k, v in artifacts.items()},
        "cases": [case_digest(c) for c in corpus.cases],
    }
    return {"payload": payload, "sha256": sha256(canonical(payload))}


def verify(manifest: dict, corpus: Corpus, artifacts: Mapping[str, bytes]) -> None:
    if manifest != freeze(corpus, manifest["payload"]["calibration"], artifacts):
        raise ValueError("Manifesto ou artefatos alterados após congelamento")
