"""CLI offline: python -m comprova_lattes.experiments --help."""

import argparse
import base64
import json
from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel

from comprova_lattes.matcher.models import ExtractedDocumentRecord, MatcherConfig

from .freeze import calibrate, freeze, verify
from .reporting import sanitize_json_value
from .runner import (
    experiment1,
    experiment2,
    experiment3,
    extraction_inference,
    inference,
    integrated_inference,
)
from .statistics import PROTOCOL_BOOTSTRAP_CONFIDENCE, PROTOCOL_BOOTSTRAP_REPLICATES
from .synthetic import Corpus, generate


def _default(value):
    if isinstance(value, ExtractedDocumentRecord):
        dumped = value.model_dump(mode="python")
        dumped["raw_metadata"] = sanitize_json_value(dumped.get("raw_metadata", {}))
        return dumped
    if isinstance(value, BaseModel):
        return value.model_dump(mode="python")
    if isinstance(value, bytes):
        return {"$bytes": base64.b64encode(value).decode("ascii")}
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(type(value).__name__)


def write(path: Path, value):
    path.write_text(
        json.dumps(value, default=_default, sort_keys=True, indent=2, allow_nan=False),
        encoding="utf-8",
    )


def read(path: Path):
    def hook(obj):
        return base64.b64decode(obj["$bytes"], validate=True) if set(obj) == {"$bytes"} else obj

    return json.loads(path.read_text(encoding="utf-8"), object_hook=hook)


def records(raw):
    return {k: ExtractedDocumentRecord.model_validate(v) for k, v in raw.items()}


class Replay:
    """Adaptador de saídas previamente capturadas, sem rede nem acesso ao gabarito."""

    def __init__(self, runs):
        self.runs, self.counts = runs, {}

    def extract(self, document_id, data, mime_type):
        index = self.counts.get(document_id, 0)
        self.counts[document_id] = index + 1
        return self.runs[index][document_id]


def _resolve_cli_bootstrap_kwargs(args) -> dict | None:
    if args.seed is None:
        if args.replicates is not None or args.confidence is not None:
            raise ValueError("Informe --seed explícita ao especificar --replicates ou --confidence")
        return None
    replicates = (
        PROTOCOL_BOOTSTRAP_REPLICATES if args.replicates is None else args.replicates
    )
    confidence = (
        PROTOCOL_BOOTSTRAP_CONFIDENCE if args.confidence is None else args.confidence
    )
    return {
        "seed": args.seed,
        "replicates": replicates,
        "confidence": confidence,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate")
    gen.add_argument("--seed", type=int, required=True)
    gen.add_argument("--pilot-families", type=int, required=True)
    gen.add_argument("--final-families", type=int, required=True)
    for name in ("calibrate", "freeze", "exp1", "exp2", "exp3"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--corpus", type=Path, required=True)
        if name == "calibrate":
            cmd.add_argument("--candidates", type=Path, required=True)
        elif name == "freeze":
            cmd.add_argument("--calibration", type=Path, required=True)
            cmd.add_argument(
                "--artifacts", type=Path, required=True, help="JSON: nome -> caminho de arquivo"
            )
        else:
            cmd.add_argument("--manifest", type=Path, required=True)
            cmd.add_argument("--artifacts", type=Path, required=True)
            cmd.add_argument("--partition", choices=("pilot", "final"), required=True)
            if name in ("exp1", "exp3"):
                cmd.add_argument(
                    "--extractions",
                    type=Path,
                    required=True,
                    help="JSON: lista de três mapas case_id -> extração",
                )
            if name == "exp1":
                cmd.add_argument("--baseline", type=Path, required=True)
            cmd.add_argument("--seed", type=int, required=name == "exp2")
            cmd.add_argument("--replicates", type=int, default=None)
            cmd.add_argument("--confidence", type=float, default=None)
    for cmd in sub.choices.values():
        cmd.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "generate":
        result = generate(
            seed=args.seed, pilot_families=args.pilot_families, final_families=args.final_families
        )
    else:
        corpus = Corpus.model_validate(read(args.corpus))
        if args.command == "calibrate":
            result = calibrate(
                corpus.select("pilot"),
                [MatcherConfig.model_validate(c) for c in read(args.candidates)],
            )
        else:
            artifacts = {k: Path(v).read_bytes() for k, v in read(args.artifacts).items()}
            if args.command == "freeze":
                result = freeze(corpus, read(args.calibration), artifacts)
            else:
                manifest = read(args.manifest)
                verify(manifest, corpus, artifacts)
                config = MatcherConfig.model_validate(manifest["payload"]["calibration"]["config"])
                cases = corpus.select(args.partition)
                bootstrap_kwargs = _resolve_cli_bootstrap_kwargs(args)
                if args.command == "exp2":
                    assert bootstrap_kwargs is not None
                    reports = experiment2(cases, config)
                    result = {
                        "reports": reports,
                        "statistics": inference(
                            reports,
                            cases,
                            **bootstrap_kwargs,
                        ),
                    }
                else:
                    runs = [records(r) for r in read(args.extractions)]
                    if len(runs) != 3:
                        raise ValueError("Exatamente três repetições obrigatórias")
                    result = (
                        experiment3(cases, runs, config)
                        if args.command == "exp3"
                        else (
                            experiment1(cases, Replay(runs), Replay([records(read(args.baseline))]))
                        )
                    )
                    if bootstrap_kwargs is not None:
                        result["statistics"] = (
                            extraction_inference(result, cases, **bootstrap_kwargs)
                            if args.command == "exp1"
                            else integrated_inference(result, cases, **bootstrap_kwargs)
                        )
                result["partition"] = args.partition
                result["freeze_sha256"] = manifest["sha256"]
    write(args.output, result)


if __name__ == "__main__":
    main()
