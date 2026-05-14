"""
Cuestionario MiFID-inspired para perfilar al inversor.

10 preguntas que cubren: tolerancia al riesgo, horizonte temporal,
objetivos, conocimiento financiero, reacción a pérdidas, preferencias ESG
y sectoriales. Cada respuesta suma puntos para calcular el perfil de riesgo.
"""

from modules.advisor.models import (
    Question,
    QuestionOption,
    QuestionnaireAnswer,
    InvestorProfile,
    RiskProfile,
    InvestmentHorizon,
    InvestmentGoal,
    KnowledgeLevel,
)


# ---------------------------------------------------------------------------
# Definición del cuestionario
# ---------------------------------------------------------------------------
QUESTIONS: list[Question] = [
    Question(
        id="q1_horizon",
        category="horizonte",
        text="¿Cuál es tu horizonte temporal de inversión?",
        description="El tiempo que planeas mantener tus inversiones antes de necesitar el dinero.",
        options=[
            QuestionOption(id="q1_a", text="Menos de 1 año", score=5),
            QuestionOption(id="q1_b", text="Entre 1 y 3 años", score=20),
            QuestionOption(id="q1_c", text="Entre 3 y 7 años", score=50),
            QuestionOption(id="q1_d", text="Entre 7 y 15 años", score=75),
            QuestionOption(id="q1_e", text="Más de 15 años", score=95),
        ],
    ),
    Question(
        id="q2_goal",
        category="objetivo",
        text="¿Cuál es tu principal objetivo de inversión?",
        description="Define qué esperas conseguir con tu cartera.",
        options=[
            QuestionOption(id="q2_a", text="Preservar mi capital, no perder dinero", score=10),
            QuestionOption(id="q2_b", text="Generar rentas periódicas (dividendos, cupones)", score=30),
            QuestionOption(id="q2_c", text="Crecimiento equilibrado del capital a medio plazo", score=55),
            QuestionOption(id="q2_d", text="Maximizar el crecimiento aceptando mayor riesgo", score=80),
            QuestionOption(id="q2_e", text="Obtener máxima rentabilidad aunque sea especulativo", score=95),
        ],
    ),
    Question(
        id="q3_loss_reaction",
        category="riesgo",
        text="Si tu cartera perdiera un 20% en un mes, ¿qué harías?",
        description="Tu reacción ante caídas fuertes del mercado revela tu tolerancia real al riesgo.",
        options=[
            QuestionOption(id="q3_a", text="Vendería todo inmediatamente para evitar más pérdidas", score=5),
            QuestionOption(id="q3_b", text="Vendería parte para reducir la exposición", score=25),
            QuestionOption(id="q3_c", text="No haría nada, esperaría a la recuperación", score=55),
            QuestionOption(id="q3_d", text="Compraría más aprovechando precios bajos", score=80),
            QuestionOption(id="q3_e", text="Aumentaría significativamente mi posición", score=95),
        ],
    ),
    Question(
        id="q4_knowledge",
        category="conocimiento",
        text="¿Cuál es tu nivel de conocimiento sobre inversiones financieras?",
        description="Sé honesto: tu nivel de conocimiento influye en los productos adecuados para ti.",
        options=[
            QuestionOption(id="q4_a", text="Ninguno – nunca he invertido ni estudiado finanzas", score=10),
            QuestionOption(id="q4_b", text="Básico – conozco acciones y depósitos", score=30),
            QuestionOption(id="q4_c", text="Intermedio – conozco ETFs, fondos, bonos y diversificación", score=55),
            QuestionOption(id="q4_d", text="Avanzado – entiendo derivados, apalancamiento y valoración", score=80),
            QuestionOption(id="q4_e", text="Experto – formación financiera y experiencia profesional", score=95),
        ],
    ),
    Question(
        id="q5_experience",
        category="experiencia",
        text="¿Cuántos años llevas invirtiendo de forma activa?",
        description="La experiencia práctica en mercados reales.",
        options=[
            QuestionOption(id="q5_a", text="Nunca he invertido", score=5),
            QuestionOption(id="q5_b", text="Menos de 2 años", score=25),
            QuestionOption(id="q5_c", text="Entre 2 y 5 años", score=50),
            QuestionOption(id="q5_d", text="Entre 5 y 10 años", score=75),
            QuestionOption(id="q5_e", text="Más de 10 años", score=95),
        ],
    ),
    Question(
        id="q6_income_stability",
        category="situación_financiera",
        text="¿Cómo describirías la estabilidad de tus ingresos actuales?",
        description="Ingresos estables permiten asumir más riesgo en inversiones.",
        options=[
            QuestionOption(id="q6_a", text="Ingresos muy variables o inciertos", score=10),
            QuestionOption(id="q6_b", text="Ingresos algo variables (autónomo, comisiones)", score=30),
            QuestionOption(id="q6_c", text="Ingresos estables con poco margen de ahorro", score=45),
            QuestionOption(id="q6_d", text="Ingresos estables con buen margen de ahorro", score=70),
            QuestionOption(id="q6_e", text="Independencia financiera / patrimonio consolidado", score=90),
        ],
    ),
    Question(
        id="q7_liquidity",
        category="liquidez",
        text="¿Qué porcentaje de tu patrimonio total representa esta cartera?",
        description="Si este dinero es una parte pequeña de tu patrimonio, puedes asumir más riesgo.",
        options=[
            QuestionOption(id="q7_a", text="Es prácticamente todo mi ahorro (>80%)", score=5),
            QuestionOption(id="q7_b", text="Es una parte importante (50-80%)", score=25),
            QuestionOption(id="q7_c", text="Es una parte significativa (25-50%)", score=50),
            QuestionOption(id="q7_d", text="Es una parte menor (10-25%)", score=75),
            QuestionOption(id="q7_e", text="Es una parte muy pequeña (<10%)", score=95),
        ],
    ),
    Question(
        id="q8_max_loss",
        category="riesgo",
        text="¿Cuál es la pérdida máxima anual que podrías tolerar sin perder el sueño?",
        description="Sé realista: marca el nivel de pérdida que aceptarías sin cambiar tu estrategia.",
        options=[
            QuestionOption(id="q8_a", text="No quiero perder nada (0%)", score=5),
            QuestionOption(id="q8_b", text="Hasta un 5% de pérdida", score=20),
            QuestionOption(id="q8_c", text="Hasta un 15% de pérdida", score=45),
            QuestionOption(id="q8_d", text="Hasta un 30% de pérdida", score=75),
            QuestionOption(id="q8_e", text="Hasta un 50% o más si el potencial es alto", score=95),
        ],
    ),
    Question(
        id="q9_esg",
        category="preferencias",
        text="¿Es importante para ti que tus inversiones cumplan criterios ESG (medioambientales, sociales y de gobernanza)?",
        description="La inversión sostenible puede limitar el universo de activos pero alinearse con tus valores.",
        options=[
            QuestionOption(id="q9_a", text="Es imprescindible, solo invierto en empresas sostenibles", score=100),
            QuestionOption(id="q9_b", text="Lo prefiero pero no es excluyente", score=70),
            QuestionOption(id="q9_c", text="Me es indiferente", score=30),
            QuestionOption(id="q9_d", text="No me importa, solo busco rentabilidad", score=0),
        ],
    ),
    Question(
        id="q10_sectors",
        category="preferencias",
        text="¿Hay sectores o temáticas en los que tengas especial interés o convicción?",
        description="Puedes seleccionar varias. Esto ayuda a personalizar las recomendaciones.",
        options=[
            QuestionOption(id="q10_a", text="Tecnología e Innovación", score=0),
            QuestionOption(id="q10_b", text="Salud y Biotecnología", score=0),
            QuestionOption(id="q10_c", text="Energía y Materias primas", score=0),
            QuestionOption(id="q10_d", text="Finanzas y Banca", score=0),
            QuestionOption(id="q10_e", text="Consumo y Retail", score=0),
            QuestionOption(id="q10_f", text="Inmobiliario (REITs)", score=0),
            QuestionOption(id="q10_g", text="Infraestructuras y Utilities", score=0),
            QuestionOption(id="q10_h", text="Sin preferencia particular", score=0),
        ],
    ),
]

# Mapa: option_id → pérdida tolerada para pregunta q8
_LOSS_TOLERANCE_MAP = {
    "q8_a": 0.0,
    "q8_b": 5.0,
    "q8_c": 15.0,
    "q8_d": 30.0,
    "q8_e": 50.0,
}

# Mapa: option_id → sector preferido para q10
_SECTOR_MAP = {
    "q10_a": "Technology",
    "q10_b": "Healthcare",
    "q10_c": "Energy",
    "q10_d": "Financial Services",
    "q10_e": "Consumer Cyclical",
    "q10_f": "Real Estate",
    "q10_g": "Utilities",
}


def get_questions() -> list[Question]:
    """Devuelve la lista completa de preguntas del cuestionario."""
    return QUESTIONS


def compute_profile(user_id: str, portfolio_id: str,
                    answers: list[QuestionnaireAnswer]) -> InvestorProfile:
    """Calcula el perfil del inversor a partir de las respuestas del cuestionario."""

    answer_map: dict[str, str] = {a.question_id: a.selected_option_id for a in answers}

    # --- Puntuación de riesgo (media ponderada de preguntas q1-q8) ---
    risk_questions = ["q1_horizon", "q2_goal", "q3_loss_reaction", "q4_knowledge",
                      "q5_experience", "q6_income_stability", "q7_liquidity", "q8_max_loss"]
    # Pesos: más peso a tolerancia al riesgo, horizonte y pérdida máxima
    weights = {
        "q1_horizon": 1.5,
        "q2_goal": 1.2,
        "q3_loss_reaction": 2.0,
        "q4_knowledge": 0.8,
        "q5_experience": 0.8,
        "q6_income_stability": 1.0,
        "q7_liquidity": 1.2,
        "q8_max_loss": 1.5,
    }

    total_score = 0.0
    total_weight = 0.0
    for qid in risk_questions:
        opt_id = answer_map.get(qid)
        if opt_id is None:
            continue
        question = next((q for q in QUESTIONS if q.id == qid), None)
        if question is None:
            continue
        option = next((o for o in question.options if o.id == opt_id), None)
        if option is None:
            continue
        w = weights.get(qid, 1.0)
        total_score += option.score * w
        total_weight += w

    risk_score = int(round(total_score / total_weight)) if total_weight > 0 else 50

    # --- Perfil de riesgo ---
    if risk_score <= 20:
        risk_profile = RiskProfile.VERY_CONSERVATIVE
    elif risk_score <= 40:
        risk_profile = RiskProfile.CONSERVATIVE
    elif risk_score <= 60:
        risk_profile = RiskProfile.MODERATE
    elif risk_score <= 80:
        risk_profile = RiskProfile.AGGRESSIVE
    else:
        risk_profile = RiskProfile.VERY_AGGRESSIVE

    # --- Horizonte (de q1) ---
    q1_opt = answer_map.get("q1_horizon", "q1_c")
    if q1_opt in ("q1_a", "q1_b"):
        horizon = InvestmentHorizon.SHORT
    elif q1_opt in ("q1_c",):
        horizon = InvestmentHorizon.MEDIUM
    else:
        horizon = InvestmentHorizon.LONG

    # --- Objetivo (de q2) ---
    q2_opt = answer_map.get("q2_goal", "q2_c")
    goal_map = {
        "q2_a": InvestmentGoal.CAPITAL_PRESERVATION,
        "q2_b": InvestmentGoal.INCOME,
        "q2_c": InvestmentGoal.BALANCED_GROWTH,
        "q2_d": InvestmentGoal.AGGRESSIVE_GROWTH,
        "q2_e": InvestmentGoal.SPECULATION,
    }
    goal = goal_map.get(q2_opt, InvestmentGoal.BALANCED_GROWTH)

    # --- Conocimiento (de q4) ---
    q4_opt = answer_map.get("q4_knowledge", "q4_c")
    knowledge_map = {
        "q4_a": KnowledgeLevel.BEGINNER,
        "q4_b": KnowledgeLevel.BEGINNER,
        "q4_c": KnowledgeLevel.INTERMEDIATE,
        "q4_d": KnowledgeLevel.ADVANCED,
        "q4_e": KnowledgeLevel.EXPERT,
    }
    knowledge = knowledge_map.get(q4_opt, KnowledgeLevel.INTERMEDIATE)

    # --- ESG (de q9) ---
    q9_opt = answer_map.get("q9_esg", "q9_c")
    esg_preference = q9_opt in ("q9_a", "q9_b")

    # --- Sectores favoritos (de q10, puede ser múltiple) ---
    sector_prefs = []
    q10_answer = answer_map.get("q10_sectors", "")
    # Soportamos respuesta múltiple separada por comas
    for opt_id in q10_answer.split(","):
        opt_id = opt_id.strip()
        if opt_id in _SECTOR_MAP:
            sector_prefs.append(_SECTOR_MAP[opt_id])

    # --- Pérdida tolerada (de q8) ---
    q8_opt = answer_map.get("q8_max_loss", "q8_c")
    loss_tolerance = _LOSS_TOLERANCE_MAP.get(q8_opt, 15.0)

    return InvestorProfile(
        user_id=user_id,
        portfolio_id=portfolio_id,
        risk_score=risk_score,
        risk_profile=risk_profile,
        horizon=horizon,
        goal=goal,
        knowledge=knowledge,
        esg_preference=esg_preference,
        sector_preferences=sector_prefs,
        loss_tolerance_pct=loss_tolerance,
        answers_raw=answers,
    )
