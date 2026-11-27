"""Textos para publicar cada vídeo (en inglés): videos/<id>_textos.txt.

FACEBOOK: texto corto con gancho, 2-3 emojis y 5 hashtags.
YOUTUBE: título (máx. 60 letras, con #shorts), descripción de 2 líneas y 5 hashtags.

El tema se deduce de lo que sale en el episodio (cantera = constancia,
mercado = negocio, taller o habitación = perfeccionismo). Las frases se eligen
a partir del id, así cada vídeo tiene textos distintos.
"""
from __future__ import annotations

import random

from .variedad import numero

TEMAS = {
    "constancia": dict(
        emojis=["🪨", "🔨", "💪", "🔥", "⛏️"],
        frases=["Most people quit right before the breakthrough.", "The rock doesn't care how tired you are.",
                "Hit number 100 only counts if you show up for it.", "Progress is invisible until it isn't.",
                "Consistency beats talent when talent stops swinging."],
        preguntas=["Which one are you today?", "Would you have stopped at 99?", "What's your rock right now?",
                   "Be honest: are you still swinging?"],
        hashtags=["#consistency", "#motivation", "#neverquit", "#discipline", "#mindset", "#persistence",
                  "#grind", "#keepgoing"],
    ),
    "negocio": dict(
        emojis=["🍋", "💰", "📈", "🧠", "💸"],
        frases=["Same product. Different thinking.", "Cheap is easy. Smart pays.",
                "Price is a decision, not a guess.", "The busiest stand isn't always the richest.",
                "Don't compete on price. Compete on value."],
        preguntas=["Which stand would you run?", "Would you raise the price?", "Cheap or smart?",
                   "What's your pricing mistake?"],
        hashtags=["#business", "#entrepreneur", "#pricing", "#smallbusiness", "#money", "#sidehustle",
                  "#businesstips", "#startup"],
    ),
    "perfeccionismo": dict(
        emojis=["✅", "🛠️", "⏱️", "✏️", "🚀"],
        frases=["Done is better than perfect.", "One builds. One plans forever.",
                "Perfect plans don't hold any weight.", "Ship it, then improve it.",
                "Your first version is supposed to be ugly."],
        preguntas=["Which one are you?", "Tag the friend who's still planning.", "Builder or planner?",
                   "What are you overthinking right now?"],
        hashtags=["#productivity", "#perfectionism", "#donenotperfect", "#procrastination", "#justdoit",
                  "#getthingsdone", "#mindset", "#selfimprovement"],
    ),
}
FIJOS = ["#shorts", "#donenotperfect"]


def tema(datos: dict) -> str:
    texto = str(datos.get("guion", ""))
    if "cantera" in texto or "'roca'" in texto:
        return "constancia"
    if "calle_mercado" in texto or "kiosco" in texto:
        return "negocio"
    return "perfeccionismo"


def _cierre_legible(cierre: str) -> str:
    if cierre.count(">") == 1:
        a, b = (x.strip() for x in cierre.split(">"))
        return f"{a} beats {b[:1].lower() + b[1:]}"
    return cierre


def generar(datos: dict) -> str:
    rnd = random.Random(numero(datos["id"], "textos"))
    t = TEMAS[tema(datos)]
    gancho = datos["textos"]["gancho"].strip()
    cierre = datos["textos"]["cierre"].strip()
    e = rnd.sample(t["emojis"], 3)
    frase = rnd.choice(t["frases"])
    pregunta = rnd.choice(t["preguntas"])
    tags_fb = ["#donenotperfect"] + rnd.sample([h for h in t["hashtags"] if h != "#donenotperfect"], 4)
    tags_yt = ["#shorts"] + rnd.sample([h for h in t["hashtags"] if h not in FIJOS], 4)

    titulo = f"{gancho} {cierre} #shorts"
    if len(titulo) > 60:
        titulo = f"{gancho} #shorts"
    if len(titulo) > 60:
        titulo = gancho[: 60 - len(" #shorts") - 1].rstrip() + "… #shorts"

    fb = f"{gancho} {e[0]}\n{frase} {e[1]}\n{_cierre_legible(cierre)}. {pregunta} {e[2]}"
    yt_desc = f"{frase} {_cierre_legible(cierre)}.\n{pregunta} Follow for a new short every day."
    return (
        "FACEBOOK\n"
        f"{fb}\n"
        f"{' '.join(tags_fb)}\n"
        "\n"
        "YOUTUBE\n"
        f"Title: {titulo}\n"
        "Description:\n"
        f"{yt_desc}\n"
        f"Hashtags: {' '.join(tags_yt)}\n"
    )
