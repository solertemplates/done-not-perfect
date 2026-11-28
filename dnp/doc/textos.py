"""Textos para publicar cada vídeo largo (en inglés y en español): <nombre>_textos.txt."""
from __future__ import annotations

import random
from urllib.parse import quote_plus

from .. import textos as tx
from ..variedad import numero
from .musica import credito

PUENTE = {
    "en": {
        "budget planner": ["Sarah's secret weapon in this story? A simple budget planner.",
                           "Every big change in Sarah's life started on one page of a budget planner."],
        "cash envelope wallet": ["Sarah's envelopes are the quietest hero of this episode.",
                                 "Cash envelopes: boring on day one, life-changing in year ten."],
        "piggy bank": ["That red piggy bank on the shelf? It matters more than it looks."],
        "Atomic Habits": ["Sarah never had a big plan, just small habits. Atomic Habits explains why that works."],
        "The Psychology of Money": ["Same salary, different thinking. The Psychology of Money is about exactly that."],
        "The Total Money Makeover": ["Mark's debt didn't start big. The Total Money Makeover is about undoing it step by step."],
    },
    "es": {
        "budget planner": ["¿El arma secreta de Sara en esta historia? Una simple agenda de presupuesto.",
                           "Cada gran cambio en la vida de Sara empezó en una página de su agenda de presupuesto."],
        "cash envelope wallet": ["Los sobres de Sara son los héroes silenciosos de este capítulo."],
        "piggy bank": ["¿Esa alcancía roja de la estantería? Importa más de lo que parece."],
        "Atomic Habits": ["Sara nunca tuvo un gran plan, solo pequeños hábitos. Hábitos atómicos explica por qué funciona."],
        "The Psychology of Money": ["Mismo sueldo, otra forma de pensar. De eso trata La psicología del dinero."],
        "The Total Money Makeover": ["La deuda de Marcos no empezó grande. La transformación total de su dinero va de deshacerla paso a paso."],
    },
}
ACCION = {
    "en": ["start your own year one", "plan your next month", "build one small habit", "keep track of every week",
           "start before the perfect moment"],
    "es": ["empezar tu propio año uno", "planear tu próximo mes", "crear un pequeño hábito", "llevar la cuenta de cada semana",
           "empezar antes del momento perfecto"],
}
LINEA2 = {"en": "{e} Get this {p} and {a} — link in the first comment 👇",
          "es": "{e} Consigue {p} para {a} — enlace en el primer comentario 👇"}
NOMBRE_ES = {"budget planner": "una agenda de presupuesto", "cash envelope wallet": "una cartera de sobres para efectivo",
             "piggy bank": "una alcancía", "Atomic Habits": "el libro Hábitos atómicos",
             "The Psychology of Money": "el libro La psicología del dinero",
             "The Total Money Makeover": "el libro La transformación total de su dinero"}
COMENTARIO_ES = ["🛒 Cómpralo aquí 👇", "🔗 Aquí está el enlace 👇", "👉 El de la historia 👇", "📦 Enlace prometido 👇",
                 "🛒 Échale un vistazo 👇", "👀 Míralo en Amazon 👇", "📌 Te ahorro la búsqueda 👇", "🧰 El que sale en el vídeo 👇",
                 "🛍️ Aquí lo tienes 👇", "🔎 Ver opciones 👇"]
DESCRIPCION = {
    "en": ["Two people. Same salary. Same city. One is constant; the other waits for the perfect moment.",
           "This is the story of Mark and Sarah, one chapter at a time.",
           "Not in a day. Not in a month. But with consistency and discipline, it happens."],
    "es": ["Dos personas. Mismo sueldo. Misma ciudad. Ella es constante; él espera el momento perfecto.",
           "Esta es la historia de Marcos y Sara, capítulo a capítulo.",
           "No en un día. No en un mes. Pero con constancia y disciplina, sucede."],
}
HASHTAGS = {"en": "#moneystory #habits #personalfinance #consistency #donenotperfect",
            "es": "#historiasdedinero #habitos #finanzaspersonales #constancia #donenotperfect"}
ETIQ = {"en": {"cap": "CHAPTERS", "hook": "Hook", "musica": "MUSIC", "sigue": "To be continued…"},
        "es": {"cap": "CAPÍTULOS", "hook": "Gancho", "musica": "MÚSICA", "sigue": "Continuará…"}}


def minutos(s: float) -> str:
    s = int(round(s))
    return f"{s // 60}:{s % 60:02d}"


def generar(g, idioma: str, linea, musicas: list[str]) -> str:
    rnd = random.Random(numero(f"{g.id}_{idioma}", "textos_largo"))
    titulo = g.cabecera.get(f"titulo_{idioma}", g.id)
    marcas = [(0.0, ETIQ[idioma]["hook"])]
    capitulos = [s for s in g.secciones if s.tipo == "capitulo"]
    for (ini, _, _), sec in zip(linea.titulos, capitulos):
        palabra = "Chapter" if idioma == "en" else "Capítulo"
        marcas.append((ini, f"{palabra} {sec.numero}: {sec.titulo[idioma].capitalize() if idioma == 'es' else sec.titulo[idioma].title()}"))
    lineas = [titulo, "", *DESCRIPCION[idioma], ""]
    if len(marcas) >= 2:
        lineas += [ETIQ[idioma]["cap"], *[f"{minutos(t)} {n}" for t, n in marcas], ""]
    pregunta = g.cabecera.get(f"pregunta_{idioma}")
    if pregunta:
        lineas += [f"{ETIQ[idioma]['sigue']} {pregunta}", ""]
    lineas += [HASHTAGS[idioma], ""]
    producto = g.cabecera.get("producto", "budget planner")
    conf = tx.amazon()
    comentario = ""
    if conf:
        puente = rnd.choice(PUENTE[idioma].get(producto) or PUENTE["en"][producto])
        emoji = rnd.choice(tx.EMOJIS_AMAZON)
        nombre = producto if idioma == "en" else NOMBRE_ES.get(producto, producto)
        lineas += [puente, LINEA2[idioma].format(e=emoji, p=nombre, a=rnd.choice(ACCION[idioma])), tx.AVISO, ""]
        tienda = conf["tienda"].removeprefix("https://").removeprefix("www.").strip("/")
        comentario = (f"\nPRIMER COMENTARIO\n{rnd.choice(tx.COMENTARIOS if idioma == 'en' else COMENTARIO_ES)}\n"
                      f"https://www.{tienda}/s?k={quote_plus(producto)}&tag={conf['id']}\n")
    if musicas:
        lineas += [ETIQ[idioma]["musica"], *[credito(m) for m in musicas], ""]
    return "\n".join(lineas).rstrip() + "\n" + comentario
