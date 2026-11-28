"""Textos para publicar cada vídeo largo (en inglés y en español): <nombre>_textos.txt."""
from __future__ import annotations

import random
from urllib.parse import quote_plus

from .. import textos as tx
from ..variedad import numero
from .musica import credito

PUENTE = {  # sin nombres: cada caso tiene personajes distintos
    "en": {
        "budget planner": ["The quiet hero of this case? A simple budget planner.",
                           "In this case, everything changed on one page of a budget planner."],
        "cash envelope wallet": ["The envelopes are the quietest evidence in this case.",
                                 "Cash envelopes: boring on day one, life-changing in year ten."],
        "piggy bank": ["That piggy bank on the shelf? In this case, it matters more than it looks."],
        "Atomic Habits": ["Nobody in this case had a big plan, just small habits. Atomic Habits explains why that works."],
        "The Psychology of Money": ["Same money, different thinking. The Psychology of Money is about exactly that."],
        "The Total Money Makeover": ["The debt in this case didn't start big. The Total Money Makeover is about undoing it step by step."],
    },
    "es": {
        "budget planner": ["¿El héroe silencioso de este caso? Una simple agenda de presupuesto.",
                           "En este caso, todo cambió en una página de una agenda de presupuesto."],
        "cash envelope wallet": ["Los sobres son la prueba más silenciosa de este caso."],
        "piggy bank": ["¿Esa alcancía de la estantería? En este caso importa más de lo que parece."],
        "Atomic Habits": ["En este caso nadie tenía un gran plan, solo pequeños hábitos. Hábitos atómicos explica por qué funciona."],
        "The Psychology of Money": ["Mismo dinero, otra forma de pensar. De eso trata La psicología del dinero."],
        "The Total Money Makeover": ["La deuda de este caso no empezó grande. La transformación total de su dinero va de deshacerla paso a paso."],
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
SERIE = {"en": "Money Cases", "es": "Casos de dinero"}
DESCRIPCION = {
    "en": ["{expediente}. {ciudad}, {anio}.",
           "Money Cases investigates ordinary people and the money decisions that quietly changed their lives. "
           "Every case starts at the end and goes back to find the moment everything turned.",
           "Not in a day. Not in a month. But with consistency and discipline, it happens."],
    "es": ["{expediente}. {ciudad}, {anio}.",
           "Casos de dinero investiga a personas normales y las decisiones de dinero que cambiaron su vida en silencio. "
           "Cada caso empieza por el final y vuelve atrás para encontrar el momento en que todo cambió.",
           "No en un día. No en un mes. Pero con constancia y disciplina, sucede."],
}
PAGINA = {"en": "", "es": "📺 Un rato con Rene"}
AVISO_FICCION = {"en": "Story dramatized for educational purposes.",
                 "es": "Historia dramatizada con fines educativos. (Story dramatized for educational purposes.)"}
HASHTAGS = {"en": "#moneycases #moneystory #habits #personalfinance #consistency",
            "es": "#casosdedinero #historiasdedinero #habitos #finanzaspersonales #unratoconrene"}
ETIQ = {"en": {"cap": "CHAPTERS", "hook": "Hook", "musica": "MUSIC", "sigue": "Next case:", "cap1": "Chapter"},
        "es": {"cap": "CAPÍTULOS", "hook": "Gancho", "musica": "MÚSICA", "sigue": "Próximo caso:", "cap1": "Capítulo"}}


def minutos(s: float) -> str:
    s = int(round(s))
    return f"{s // 60}:{s % 60:02d}"


def generar(g, idioma: str, linea, musicas: list[str]) -> str:
    rnd = random.Random(numero(f"{g.id}_{idioma}", "textos_largo"))
    titulo = g.cab(idioma, "titulo", g.id)
    expediente = g.cab(idioma, "expediente")
    if expediente and not titulo.upper().startswith(expediente.split(":")[0].upper()):
        titulo = f"{titulo} | {SERIE[idioma]} — {expediente.split(':')[0].strip().title()}"
    marcas = [(0.0, ETIQ[idioma]["hook"])]
    capitulos = [s for s in g.secciones if s.tipo == "capitulo"]
    for (ini, _, _), sec in zip(linea.titulos, capitulos):
        nombre = sec.titulo[idioma].capitalize() if idioma == "es" else sec.titulo[idioma].title()
        marcas.append((ini, f"{ETIQ[idioma]['cap1']} {sec.numero}: {nombre}"))
    datos = {"expediente": expediente or SERIE[idioma], "ciudad": g.cab(idioma, "ciudad"), "anio": g.cab(idioma, "anio")}
    lineas = [titulo, "", *[x.format(**datos) for x in DESCRIPCION[idioma]], ""]
    if PAGINA[idioma]:
        lineas += [PAGINA[idioma], ""]
    if len(marcas) >= 2:
        lineas += [ETIQ[idioma]["cap"], *[f"{minutos(t)} {n}" for t, n in marcas], ""]
    siguiente, pregunta = g.cab(idioma, "siguiente"), g.cab(idioma, "pregunta")
    if siguiente or pregunta:
        lineas += [f"{ETIQ[idioma]['sigue']} {' — '.join(x for x in (siguiente, pregunta) if x)}", ""]
    lineas += [HASHTAGS[idioma], ""]
    producto = g.cab("en", "producto", "budget planner")
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
    lineas += [AVISO_FICCION[idioma]]
    return "\n".join(lineas).rstrip() + "\n" + comentario
