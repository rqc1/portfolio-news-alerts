"""
Visor de resultados de comparación multi-modelo.
Ejecutar: python scripts/_show_comparison.py
"""
import json
from pathlib import Path

f = Path(__file__).parent / "model_comparison_results.json"
d = json.load(open(f, "r", encoding="utf-8"))

print(f"\n{'═'*80}")
print(f"COMPARACIÓN MULTI-MODELO — {d['timestamp'][:19]}")
print(f"{'═'*80}")
print(f"Cartera: {d['portfolio']}  ({', '.join(d['tickers'])})")
print(f"Noticias: {d['relevant_news']} relevantes de {d['total_news']} totales")
print(f"Modelos: {len(d['models_compared'])}  |  Tiempo: {d['elapsed_seconds']}s")

print(f"\n{'─'*80}")
print("RESUMEN POR MODELO")
print(f"{'─'*80}")
print(f"  {'MODELO':<30s} {'OK':>5s} {'ERR':>5s} {'SEV':>7s} {'CONF':>7s} {'LAT':>7s}")
print(f"  {'─'*30} {'─'*5} {'─'*5} {'─'*7} {'─'*7} {'─'*7}")
for name, v in d["model_summaries"].items():
    ok = v["total"] - v["errors"]
    sev = f"{v['avg_severity']:.3f}" if ok > 0 else "—"
    conf = f"{v['avg_confidence']:.3f}" if ok > 0 else "—"
    # Calcular latencia media
    lats = []
    for r in d.get("results", []):
        mr = r.get("model_results", {}).get(name, {})
        if "error" not in mr and "latency_s" in mr:
            lats.append(mr["latency_s"])
    lat = f"{sum(lats)/len(lats):.1f}s" if lats else "—"
    print(f"  {name:<30s} {ok:>5d} {v['errors']:>5d} {sev:>7s} {conf:>7s} {lat:>7s}")

print(f"\n  Distribución de direcciones por modelo:")
for name, v in d["model_summaries"].items():
    dirs = v.get("directions", {})
    if any(v2 > 0 for v2 in dirs.values()):
        parts = [f"{k}={v2}" for k, v2 in dirs.items() if v2 > 0]
        print(f"    {name:<30s} {', '.join(parts)}")

print(f"\n{'─'*80}")
print("ACUERDO INTER-MODELO")
print(f"{'─'*80}")
print(f"  {'PAR DE MODELOS':<55s} {'EVENTO':>7s} {'DIR':>7s} {'MAE':>7s} {'N':>4s}")
print(f"  {'─'*55} {'─'*7} {'─'*7} {'─'*7} {'─'*4}")
for k, v in d["agreement_metrics"].items():
    evt = f"{v['event_agreement']*100:.0f}%"
    dr = f"{v['direction_agreement']*100:.0f}%"
    mae = f"{v['severity_mae']:.4f}" if v.get("severity_mae") is not None else "—"
    print(f"  {k:<55s} {evt:>7s} {dr:>7s} {mae:>7s} {v['n']:>4d}")

print(f"\n{'─'*80}")
print("DETALLE POR NOTICIA")
print(f"{'─'*80}")
for r in d.get("results", []):
    print(f"\n  📰 {r['title'][:75]}")
    print(f"     Relevancia: {r['relevance_score']:.3f}  |  Assets: {r['matched_assets']}")
    print(f"     NLP: {r['nlp_event_type']}  |  Det: dir={r['deterministic_impact']['direction']}, sev={r['deterministic_impact']['severity']:.2f}")
    for model_name, mr in r["model_results"].items():
        if "error" in mr:
            print(f"     ❌ {model_name:<28s}  ERROR: {mr['error'][:50]}")
        else:
            print(f"     ✅ {model_name:<28s}  {mr['event_type']:<15s} {mr['direction']:<8s} sev={mr['severity']:.2f} conf={mr['confidence']:.2f} ({mr.get('latency_s',0):.1f}s)")

print(f"\n{'═'*80}")
print(f"Archivo: {f}")
print(f"{'═'*80}\n")
