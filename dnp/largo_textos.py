"""Textos para publicar un vídeo largo (videos/<id>_textos.txt), en inglés.

Título, descripción, CAPÍTULOS con sus minutos, hashtags, producto de Amazon que se
ve en el vídeo (piggy bank o Atomic Habits) y el apartado PRIMER COMENTARIO.
Es una historia sobre hábitos: sin promesas de éxito ni de dinero.
"""
from __future__ import annotations

import re
from urllib.parse import quote_plus

from . import textos as tx

PUENTES = {
    "piggy bank": [
        "The piggy bank in this video never asked for a big amount, just a regular one.",
        "Same salary, two piggy banks. One got a little every month.",
        "A piggy bank is boring on day 1 and interesting in year 10.",
        "Watch the piggy bank on the left: small coins, every month, no drama.",
        "Nothing fancy here, just a piggy bank and a habit.",
        "The piggy bank is the slowest character in this story, and the most consistent.",
        "Two piggy banks, same starting point. The difference is the habit.",
        "A piggy bank only needs one thing: that you show up again next month.",
        "This whole story fits inside a piggy bank.",
        "The coins are small. The habit is the point.",
    ],
    "Atomic Habits": [
        "This video is Atomic Habits told with two stick figures.",
        "Small things, repeated: that is the whole idea behind Atomic Habits.",
        "If the calendar full of green marks hit home, Atomic Habits goes deeper.",
        "Atomic Habits is the long version of this story.",
        "Why do small habits win over ten years? Atomic Habits has a theory.",
        "The Doer never read a perfect plan. He just repeated small habits.",
        "Every green mark in this video is a tiny habit.",
        "Atomic Habits is about the days nobody posts about.",
        "Same salary, different habits: that is what Atomic Habits explains.",
        "Waiting for the perfect moment is the habit Atomic Habits helps you break.",
    ],
}
ACCIONES = {
    "piggy bank": ["start saving a little every month", "build your first saving habit", "put something aside this week",
                   "start small today", "make saving automatic", "track your monthly habit",
                   "give your coins a home", "start your own year 1", "save first, then spend",
                   "keep the habit going"],
    "Atomic Habits": ["build one small habit this week", "start your year 1 today", "make your habits easier",
                      "stop waiting for the perfect moment", "repeat small things every day",
                      "fill your own calendar with green marks", "design your daily routine",
                      "choose done over perfect", "keep going when it gets boring", "make consistency simple"],
}


def producto(largo) -> str:
    """Un objeto que se ve en el vídeo: la hucha (si hay capítulo de ahorro) o el libro, alternando."""
    m = re.match(r"largo(\d+)", largo.id)
    n = int(m.group(1)) if m else 1
    if "savings" in largo.capitulos and n % 2 == 1:
        return "piggy bank"
    return "Atomic Habits"


def minutos(segundos: float) -> str:
    s = int(round(segundos))
    return f"{s // 60}:{s % 60:02d}"


def generar(largo) -> str:
    ident = largo.id
    prod = producto(largo)
    nombre = f"{prod} book" if prod == "Atomic Habits" else prod
    puente = tx._elige(PUENTES[prod], ident, "puente_largo", 3)
    accion = tx._elige(ACCIONES[prod], ident, "accion_largo", 7)
    emoji = tx._elige(tx.EMOJIS_AMAZON, ident, "emoji", 5)
    comentario = tx._elige(tx.COMENTARIOS, ident, "comentario", 7)
    conf = tx.amazon()
    titulo = f"{largo.gancho} | Done, not perfect"
    if len(titulo) > 100:
        titulo = largo.gancho[:100]
    capitulos = "\n".join(f"{minutos(t)} {nombre_cap}" for t, nombre_cap in largo.marcas())
    hashtags = "#donenotperfect #habits #consistency #discipline #" + ("savings" if "savings" in largo.capitulos
                                                                        else "selfimprovement")
    lineas = [
        "TITLE",
        titulo,
        "",
        "DESCRIPTION",
        "Two people. Same salary. One does a little every month; the other waits for the perfect moment.",
        "A story about habits told in 10 years, with no words, just two stick figures.",
        largo.mensaje,
        "",
        "CHAPTERS",
        capitulos,
        "",
        f"Next: {largo.siguiente}",
        "",
        hashtags,
    ]
    texto = "\n".join(lineas) + "\n"
    if conf:
        tienda = conf["tienda"].removeprefix("https://").removeprefix("www.").strip("/")
        enlace = f"https://www.{tienda}/s?k={quote_plus(prod)}&tag={conf['id']}"
        texto += (f"\n{puente}\n{emoji} Get this {nombre} and {accion} — link in the first comment 👇\n{tx.AVISO}\n"
                  f"\nPRIMER COMENTARIO\n{comentario}\n{enlace}\n")
    return texto
