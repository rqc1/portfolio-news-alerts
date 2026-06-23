"""
Cálculo del acuerdo inter-anotador del corpus de evaluación.

Compara las etiquetas del anotador 1 (`evaluation/dataset.jsonl`, ground truth
de referencia) con las del anotador 2 (`evaluation/dataset_annotator2.jsonl`,
re-anotación independiente de un subconjunto) y reporta, por dimensión:

  - is_relevant: % acuerdo + κ de Cohen
  - event_type:  % acuerdo + κ de Cohen
  - direction:   % acuerdo + κ de Cohen
  - severity_label: % acuerdo + κ ponderado (cuadrático) + α de Krippendorff
    ordinal

Uso:
    python -m evaluation.run_agreement [--save evaluation/results/agreement.json]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluation.agreement import agreement_report

EVAL_DIR = Path(__file__).parent
ANNOTATOR1 = EVAL_DIR / "dataset.jsonl"
ANNOTATOR2 = EVAL_DIR / "dataset_annotator2.jsonl"
DEFAULT_OUT = EVAL_DIR / "results" / "agreement.json"


def _load_labels(path: Path) -> dict[str, dict]:
    annotations: dict[str, dict] = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            labels = row["labels"]
            annotations[row["id"]] = {
                "is_relevant": labels["is_relevant"],
                "event_type": labels["event_type"],
                "direction": labels["direction"],
                "severity_label": labels["severity_label"],
            }
    return annotations


def main() -> None:
    parser = argparse.ArgumentParser(description="Acuerdo inter-anotador")
    parser.add_argument("--save", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    a1 = _load_labels(ANNOTATOR1)
    a2 = _load_labels(ANNOTATOR2)

    report = agreement_report(a1, a2)

    out_path = Path(args.save)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Ítems comunes evaluados: {report['n_common_items']}")
    print("-" * 60)
    for dim, stats in report["dimensions"].items():
        print(f"[{dim}]")
        for k, v in stats.items():
            print(f"    {k}: {v}")
    print("-" * 60)
    print(f"Reporte guardado en: {out_path}")


if __name__ == "__main__":
    main()
