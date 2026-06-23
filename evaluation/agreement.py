"""
Acuerdo inter-anotador (Inter-Annotator Agreement, IAA).

Justificación académica: un corpus etiquetado por un único anotador no permite
estimar la fiabilidad de las etiquetas gold. Para sostener la validez del
ground truth se mide el grado de acuerdo entre dos o más anotadores
independientes sobre el mismo subconjunto de noticias.

Este módulo implementa, sin dependencias externas (puro Python):

  - `percentage_agreement`: acuerdo observado bruto (porcentaje).
  - `cohen_kappa`: κ de Cohen para 2 anotadores y etiquetas nominales.
  - `weighted_cohen_kappa`: κ ponderado (lineal/cuadrático) para etiquetas
    ORDINALES (p.ej. severidad muy_baja..muy_alta), que penaliza menos los
    desacuerdos entre categorías cercanas.
  - `fleiss_kappa`: κ de Fleiss para ≥2 anotadores (formato de conteos).
  - `krippendorff_alpha`: α de Krippendorff (nominal u ordinal), robusto a
    datos faltantes y número variable de anotadores.

Interpretación de κ/α (escala de Landis & Koch, 1977):
    < 0.00  pobre
    0.00–0.20  leve
    0.21–0.40  aceptable
    0.41–0.60  moderado
    0.61–0.80  sustancial
    0.81–1.00  casi perfecto
"""

from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Hashable, Sequence


# ---------------------------------------------------------------------------
# Interpretación cualitativa
# ---------------------------------------------------------------------------
def interpret_kappa(value: float) -> str:
    """Etiqueta cualitativa (Landis & Koch) para un valor de κ/α."""
    if value < 0.0:
        return "pobre"
    if value <= 0.20:
        return "leve"
    if value <= 0.40:
        return "aceptable"
    if value <= 0.60:
        return "moderado"
    if value <= 0.80:
        return "sustancial"
    return "casi_perfecto"


# ---------------------------------------------------------------------------
# Acuerdo porcentual
# ---------------------------------------------------------------------------
def percentage_agreement(a: Sequence[Hashable], b: Sequence[Hashable]) -> float:
    """Proporción de ítems en los que dos anotadores coinciden (0–1)."""
    if len(a) != len(b):
        raise ValueError("Las dos listas de anotaciones deben tener igual longitud")
    if not a:
        return 0.0
    agree = sum(1 for x, y in zip(a, b) if x == y)
    return agree / len(a)


# ---------------------------------------------------------------------------
# Cohen's kappa (2 anotadores, nominal)
# ---------------------------------------------------------------------------
def cohen_kappa(a: Sequence[Hashable], b: Sequence[Hashable]) -> float:
    """κ de Cohen para dos anotadores y etiquetas nominales.

    κ = (p_o - p_e) / (1 - p_e), donde p_o es el acuerdo observado y p_e el
    acuerdo esperado por azar a partir de las distribuciones marginales.
    """
    if len(a) != len(b):
        raise ValueError("Las dos listas de anotaciones deben tener igual longitud")
    n = len(a)
    if n == 0:
        return 0.0

    p_o = percentage_agreement(a, b)

    count_a = Counter(a)
    count_b = Counter(b)
    labels = set(count_a) | set(count_b)
    p_e = sum((count_a[l] / n) * (count_b[l] / n) for l in labels)

    if p_e == 1.0:
        # Acuerdo perfecto trivial (una sola categoría): κ indefinido → 1.0.
        return 1.0
    return (p_o - p_e) / (1.0 - p_e)


# ---------------------------------------------------------------------------
# Weighted Cohen's kappa (2 anotadores, ordinal)
# ---------------------------------------------------------------------------
def weighted_cohen_kappa(
    a: Sequence[Hashable],
    b: Sequence[Hashable],
    categories: Sequence[Hashable],
    weights: str = "linear",
) -> float:
    """κ ponderado para etiquetas ORDINALES.

    `categories` define el orden de las categorías (índice = rango ordinal).
    `weights`: 'linear' penaliza proporcionalmente a la distancia ordinal;
    'quadratic' penaliza el cuadrado de la distancia.
    """
    if len(a) != len(b):
        raise ValueError("Las dos listas de anotaciones deben tener igual longitud")
    n = len(a)
    if n == 0:
        return 0.0

    idx = {cat: i for i, cat in enumerate(categories)}
    k = len(categories)
    if k <= 1:
        return 1.0

    def dist_weight(i: int, j: int) -> float:
        d = abs(i - j)
        if weights == "quadratic":
            return (d / (k - 1)) ** 2
        return d / (k - 1)

    # Matrices observada y esperada.
    observed = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b):
        observed[idx[x]][idx[y]] += 1

    row = [sum(observed[i]) for i in range(k)]
    col = [sum(observed[i][j] for i in range(k)) for j in range(k)]

    num = 0.0
    den = 0.0
    for i in range(k):
        for j in range(k):
            w = dist_weight(i, j)
            expected = row[i] * col[j] / n
            num += w * observed[i][j]
            den += w * expected
    if den == 0:
        return 1.0
    return 1.0 - num / den


# ---------------------------------------------------------------------------
# Fleiss' kappa (>=2 anotadores, nominal)
# ---------------------------------------------------------------------------
def fleiss_kappa(ratings: Sequence[Sequence[Hashable]]) -> float:
    """κ de Fleiss para múltiples anotadores con el MISMO número por ítem.

    `ratings`: lista de ítems; cada ítem es la lista de etiquetas asignadas
    por los anotadores (p.ej. [["alta","alta","media"], ...]).
    Requiere igual número de anotadores por ítem.
    """
    n_items = len(ratings)
    if n_items == 0:
        return 0.0
    n_raters = len(ratings[0])
    if any(len(r) != n_raters for r in ratings):
        raise ValueError("Fleiss requiere el mismo número de anotadores por ítem")
    if n_raters <= 1:
        return 1.0

    categories = sorted({label for item in ratings for label in item}, key=str)
    cat_index = {c: i for i, c in enumerate(categories)}
    k = len(categories)

    # Matriz n_items x k de conteos.
    counts = [[0] * k for _ in range(n_items)]
    for i, item in enumerate(ratings):
        for label in item:
            counts[i][cat_index[label]] += 1

    # P_i: acuerdo dentro de cada ítem.
    p_i = []
    for i in range(n_items):
        s = sum(counts[i][j] * (counts[i][j] - 1) for j in range(k))
        p_i.append(s / (n_raters * (n_raters - 1)))
    p_bar = sum(p_i) / n_items

    # p_j: proporción de asignaciones a cada categoría.
    total = n_items * n_raters
    p_j = [sum(counts[i][j] for i in range(n_items)) / total for j in range(k)]
    p_e = sum(p * p for p in p_j)

    if p_e == 1.0:
        return 1.0
    return (p_bar - p_e) / (1.0 - p_e)


# ---------------------------------------------------------------------------
# Krippendorff's alpha (nominal u ordinal, datos faltantes admitidos)
# ---------------------------------------------------------------------------
def krippendorff_alpha(
    annotations: Sequence[Sequence],
    level: str = "nominal",
    categories: Sequence[Hashable] | None = None,
) -> float:
    """α de Krippendorff.

    `annotations`: una lista por anotador; cada lista contiene la etiqueta de
    ese anotador para cada ítem, usando None para valores faltantes. Todas las
    listas deben tener la misma longitud (alineadas por ítem).
    `level`: 'nominal' u 'ordinal' (este último requiere `categories` con el
    orden de las etiquetas).
    """
    if not annotations:
        return 0.0
    n_items = len(annotations[0])
    if any(len(row) != n_items for row in annotations):
        raise ValueError("Todas las listas de anotadores deben tener igual longitud")

    # Construir, por ítem, la lista de valores observados (sin faltantes).
    units = []
    for j in range(n_items):
        vals = [row[j] for row in annotations if row[j] is not None]
        if len(vals) >= 2:  # solo ítems con ≥2 anotaciones aportan a α
            units.append(vals)

    if not units:
        return 0.0

    # Función de distancia métrica.
    if level == "ordinal":
        if categories is None:
            raise ValueError("El nivel 'ordinal' requiere 'categories'")
        rank = {c: i for i, c in enumerate(categories)}

        def delta(x, y) -> float:
            return (rank[x] - rank[y]) ** 2
    else:
        def delta(x, y) -> float:
            return 0.0 if x == y else 1.0

    # Desacuerdo observado D_o.
    num_o = 0.0
    total_pairs = 0
    for vals in units:
        m = len(vals)
        for x, y in combinations(vals, 2):
            num_o += delta(x, y)
        # cada par cuenta una vez; normalización por (m-1) como en Krippendorff
        # usando ponderación 1/(m-1).
    # Implementación estándar basada en coincidencias por unidad:
    # D_o = (1/sum(m_u)) * sum_u (1/(m_u-1)) * sum_{x<y} delta
    sum_m = sum(len(v) for v in units)
    num_o = 0.0
    for vals in units:
        m = len(vals)
        s = sum(delta(x, y) for x, y in combinations(vals, 2))
        num_o += s / (m - 1)
    d_o = num_o / sum_m if sum_m else 0.0

    # Desacuerdo esperado D_e sobre todos los valores agrupados.
    all_vals = [v for vals in units for v in vals]
    nv = len(all_vals)
    if nv <= 1:
        return 1.0
    num_e = sum(
        delta(all_vals[i], all_vals[j])
        for i in range(nv)
        for j in range(nv)
        if i != j
    )
    d_e = num_e / (nv * (nv - 1))

    if d_e == 0:
        return 1.0
    return 1.0 - d_o / d_e


# ---------------------------------------------------------------------------
# Reporte agregado sobre dos anotadores y varias dimensiones
# ---------------------------------------------------------------------------
def agreement_report(
    annotator_a: dict[str, dict],
    annotator_b: dict[str, dict],
    severity_order: Sequence[str] = ("muy_baja", "baja", "media", "alta", "muy_alta"),
    direction_labels: Sequence[str] = ("alcista", "bajista", "neutral"),
) -> dict:
    """Calcula IAA por dimensión sobre los ítems comunes a ambos anotadores.

    Cada anotador es un dict {item_id: {is_relevant, event_type, direction,
    severity_label}}. Se evalúan: is_relevant (nominal binario), event_type
    (nominal), direction (nominal) y severity_label (ordinal, κ ponderado y α
    ordinal).
    """
    common_ids = sorted(set(annotator_a) & set(annotator_b))
    report: dict = {"n_common_items": len(common_ids), "dimensions": {}}
    if not common_ids:
        return report

    def col(annot: dict, field: str) -> list:
        return [annot[i][field] for i in common_ids]

    # is_relevant (nominal binario)
    a_rel, b_rel = col(annotator_a, "is_relevant"), col(annotator_b, "is_relevant")
    report["dimensions"]["is_relevant"] = {
        "percentage_agreement": round(percentage_agreement(a_rel, b_rel), 4),
        "cohen_kappa": round(cohen_kappa(a_rel, b_rel), 4),
        "interpretation": interpret_kappa(cohen_kappa(a_rel, b_rel)),
    }

    # event_type (nominal)
    a_ev, b_ev = col(annotator_a, "event_type"), col(annotator_b, "event_type")
    report["dimensions"]["event_type"] = {
        "percentage_agreement": round(percentage_agreement(a_ev, b_ev), 4),
        "cohen_kappa": round(cohen_kappa(a_ev, b_ev), 4),
        "interpretation": interpret_kappa(cohen_kappa(a_ev, b_ev)),
    }

    # direction (nominal)
    a_dir, b_dir = col(annotator_a, "direction"), col(annotator_b, "direction")
    report["dimensions"]["direction"] = {
        "percentage_agreement": round(percentage_agreement(a_dir, b_dir), 4),
        "cohen_kappa": round(cohen_kappa(a_dir, b_dir), 4),
        "interpretation": interpret_kappa(cohen_kappa(a_dir, b_dir)),
    }

    # severity_label (ordinal)
    a_sev, b_sev = col(annotator_a, "severity_label"), col(annotator_b, "severity_label")
    wk = weighted_cohen_kappa(a_sev, b_sev, severity_order, weights="quadratic")
    alpha = krippendorff_alpha(
        [a_sev, b_sev], level="ordinal", categories=severity_order
    )
    report["dimensions"]["severity_label"] = {
        "percentage_agreement": round(percentage_agreement(a_sev, b_sev), 4),
        "weighted_cohen_kappa_quadratic": round(wk, 4),
        "krippendorff_alpha_ordinal": round(alpha, 4),
        "interpretation": interpret_kappa(wk),
    }

    return report
