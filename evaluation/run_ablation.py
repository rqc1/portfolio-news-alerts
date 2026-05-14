"""
CLI principal de evaluación: ejecuta un ablation study sobre el corpus
etiquetado y genera un informe comparativo de las cuatro variantes.

Uso:
    python -m evaluation.run_ablation                      # ejecuta todas las variantes
    python -m evaluation.run_ablation --variants rules hybrid
    python -m evaluation.run_ablation --output results.json

Salidas:
    - stdout: tabla resumen comparativa por variante
    - evaluation/results/<variant>_predictions.jsonl
    - evaluation/results/<variant>_metrics.json
    - evaluation/results/ablation_summary.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path

from evaluation.metrics import evaluate_predictions, format_report
from evaluation.runner import (
    PipelineRunner,
    VARIANTS,
    load_dataset,
    load_portfolios,
    predictions_to_jsonl,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ablation")

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def _summary_row(variant: str, results: dict) -> dict:
    """Extrae métricas clave de cada variante para la tabla comparativa."""
    return {
        "variant": variant,
        "relevance_f1": results["relevance"]["f1"],
        "relevance_precision": results["relevance"]["precision"],
        "relevance_recall": results["relevance"]["recall"],
        "matched_assets_f1": results["matched_assets"]["micro_f1"],
        "matched_assets_jaccard": results["matched_assets"]["mean_jaccard"],
        "event_type_macro_f1": results["event_type"]["macro"]["f1"],
        "event_type_accuracy": results["event_type"]["accuracy"],
        "direction_accuracy": results["direction"]["accuracy"],
        "direction_macro_f1": results["direction"]["macro"]["f1"],
        "severity_mae": results["severity"]["mae"],
        "severity_off_by_one": results["severity"]["off_by_one_or_less"],
    }


def _format_summary_table(rows: list[dict]) -> str:
    """Tabla compacta con las métricas clave por variante."""
    if not rows:
        return "(sin resultados)"
    headers = [
        ("variant", "Variante", "<14"),
        ("relevance_f1", "RelF1", ">7.3f"),
        ("relevance_precision", "RelP", ">7.3f"),
        ("relevance_recall", "RelR", ">7.3f"),
        ("matched_assets_f1", "AssF1", ">7.3f"),
        ("event_type_macro_f1", "EvF1m", ">7.3f"),
        ("direction_accuracy", "DirAcc", ">7.3f"),
        ("severity_mae", "SevMAE", ">7.3f"),
    ]

    def _fmt(value, spec: str) -> str:
        if isinstance(value, str):
            spec_val = spec.replace("d", "").replace("f", "")
            try:
                return f"{value:{spec}}"
            except (TypeError, ValueError):
                return f"{value:{spec_val}}"
        return f"{value:{spec}}"

    header_line = " | ".join(f"{label:>7}" if i > 0 else f"{label:<14}"
                             for i, (_, label, _) in enumerate(headers))
    sep = "-" * len(header_line)
    lines = [header_line, sep]
    for row in rows:
        cells = []
        for i, (key, _, spec) in enumerate(headers):
            cells.append(_fmt(row[key], spec))
        lines.append(" | ".join(cells))
    return "\n".join(lines)


async def main_async(args: argparse.Namespace) -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    dataset = load_dataset()
    portfolios = load_portfolios()
    logger.info("Dataset: %d ejemplos | Carteras: %d", len(dataset), len(portfolios))

    selected_variants = args.variants or list(VARIANTS)
    summary_rows: list[dict] = []

    for variant in selected_variants:
        logger.info("=== Ejecutando variante: %s ===", variant)
        runner = PipelineRunner(variant=variant)
        # En caso de degradación full -> hybrid_nli, registramos el efectivo
        effective_variant = runner.variant
        predictions = await runner.run_all(dataset, portfolios)

        # Persistir predicciones
        pred_path = RESULTS_DIR / f"{variant}_predictions.jsonl"
        pred_path.write_text(predictions_to_jsonl(predictions), encoding="utf-8")

        # Calcular métricas
        results = evaluate_predictions(dataset, predictions)
        results["variant_requested"] = variant
        results["variant_effective"] = effective_variant

        metrics_path = RESULTS_DIR / f"{variant}_metrics.json"
        metrics_path.write_text(json.dumps(results, indent=2, ensure_ascii=False),
                                encoding="utf-8")

        print("\n" + format_report(results, variant=f"{variant} (efectiva: {effective_variant})"))
        summary_rows.append(_summary_row(variant, results))

    # Tabla comparativa
    print("\n\n" + "=" * 70)
    print("RESUMEN COMPARATIVO (ablation study)")
    print("=" * 70)
    print(_format_summary_table(summary_rows))

    summary_path = RESULTS_DIR / "ablation_summary.json"
    summary_path.write_text(json.dumps(summary_rows, indent=2, ensure_ascii=False),
                            encoding="utf-8")
    logger.info("Resultados guardados en %s", RESULTS_DIR)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ablation study del pipeline InvestAIlert")
    parser.add_argument(
        "--variants",
        nargs="+",
        choices=list(VARIANTS),
        help="Variantes a evaluar (por defecto: todas)",
    )
    args = parser.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
