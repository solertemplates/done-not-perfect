"""Textos para publicar cada vídeo (en inglés): videos/<id>_textos.txt.

FACEBOOK: texto corto con gancho, 2-3 emojis y 5 hashtags.
YOUTUBE: título (máx. 60 letras, con #shorts), descripción de 2 líneas y 5 hashtags.

El tema se deduce de lo que sale en el episodio (cantera = constancia,
mercado = negocio, taller o habitación = perfeccionismo). Las frases se eligen
a partir del id, así cada vídeo tiene textos distintos.
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from urllib.parse import quote_plus

from .variedad import numero

RAIZ = Path(__file__).resolve().parent.parent
AMAZON = RAIZ / "config" / "amazon.txt"
AVISO = "As an Amazon Associate I earn from qualifying purchases."

# --- AMAZON -------------------------------------------------------------------------------
# El producto es siempre un objeto que SE VE en el vídeo. El primero de la lista es el preferido;
# si el episodio anterior llevaba el mismo, se usa el siguiente objeto visible.
PRODUCTOS = {
    "constancia": ["sledgehammer", "Atomic Habits"],
    "silla": ["desk chair"],
    "escalera": ["step ladder"],
    "dinero": ["lemonade dispenser"],
    "martillos": ["home tool kit"],
}
LAMPARA, PORTATIL = "desk lamp", "laptop"

# Lección de cada categoría (para la frase puente). Sin promesas de éxito ni de dinero.
LECCIONES = {
    "constancia": ["What changes the result is the hit after you wanted to stop.",
                   "The difference is who keeps going when it gets boring.",
                   "Quitting at 99 feels the same as never starting."],
    "silla": ["The one who finishes the wobbly version is the one who gets to sit down.",
              "A finished chair beats a perfect drawing of one.",
              "Done first, better later."],
    "escalera": ["Building it beats drawing it perfectly.",
                 "One real step is worth more than a perfect plan.",
                 "You can only climb what you actually build."],
    "dinero": ["The difference is how you think about value.",
               "Same lemonade, different thinking.",
               "Cheap is easy to copy; smart is not."],
    "martillos": ["Done beats perfect, nail after nail.",
                  "One hammer measures, the other one finishes.",
                  "Measuring forever never built anything."],
}
# Frases puente: unen el objeto que se ve con la lección ({p} = producto, {l} = lección).
PUENTES = [
    "Notice the {p} in this short? {l}",
    "Both of them had the same {p}. {l}",
    "The {p} is not the difference here. {l}",
    "Same {p} on both sides of the screen. {l}",
    "A {p} is just a tool until someone uses it. {l}",
    "Nothing fancy in this video, just a {p}. {l}",
    "The {p} stays the same; the result doesn't. {l}",
    "Look closely at the {p}. {l}",
    "Give two people the same {p} and watch. {l}",
    "This short is really about a {p}. {l}",
    "Watch what each one does with the {p}. {l}",
    "It was never about having a better {p}. {l}",
]
PUENTES_LIBRO = [  # cuando el producto es un libro (no un objeto de la escena)
    "This short is Atomic Habits in 15 seconds. {l}",
    "Atomic Habits explains what you just watched. {l}",
    "Small repeated hits are the whole idea behind Atomic Habits. {l}",
    "If this short hit home, Atomic Habits goes deeper. {l}",
    "Atomic Habits is the long version of this rock. {l}",
    "The rock is a metaphor; Atomic Habits is the manual. {l}",
    "Every hit in this video is a habit. {l}",
    "Atomic Habits is about the hits nobody sees. {l}",
    "Why does hit 100 work? Atomic Habits has a theory. {l}",
    "Same rock, same tool, different habits. {l}",
]
ACCIONES = {
    "constancia": ["keep swinging", "take one more hit today", "show up again tomorrow", "count your reps, not your doubts",
                   "finish what you started", "go for hit 100", "stop waiting to feel ready",
                   "keep going when it gets boring", "build the habit one hit at a time", "trust the boring part"],
    "silla": ["build the imperfect version first", "finish before you polish", "sit on something you actually finished",
              "stop redrawing and start building", "make it real today", "build it, then fix it",
              "choose done over perfect", "start with what you have", "get your project off the paper",
              "finish one thing this week"],
    "escalera": ["climb one step at a time", "take the first step today", "start before the plan is perfect",
                 "build your next step", "go up one rung today", "stop measuring and start climbing",
                 "turn the sketch into real steps", "make progress you can stand on", "take the next small step",
                 "build instead of overplanning"],
    "dinero": ["think about value, not just price", "run your stand your way", "learn from the smart stand",
               "set up your summer stand", "price with a plan", "serve your first customers",
               "keep it simple and open today", "try your idea for real", "set up your first stand",
               "test your idea this weekend"],
    "martillos": ["fix that thing you keep postponing", "finish the project in your garage", "start the repair today",
                  "nail it, then improve it", "stop measuring and start hammering", "handle the small fixes this weekend",
                  "get the job done, not perfect", "build something with your hands", "tackle your to-do list",
                  "finish one fix today"],
}
EMOJIS_AMAZON = ["🧰", "🛠️", "🔧", "✅", "🚀", "📦", "⭐", "💪", "🎯", "✨", "🔥", "👉"]
COMENTARIOS = ["🛒 Shop now 👇", "🛒 Grab yours here 👇", "🔗 Find it here 👇", "🛒 Check it out 👇",
               "👀 See it on Amazon 👇", "🧰 The one from the video 👇", "📦 Link as promised 👇",
               "🛒 Take a look 👇", "👉 Here's the link 👇", "🔎 Browse the options 👇", "🛍️ Have a look here 👇",
               "📌 Saved you a search 👇"]
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
    if "cantera" in texto or "'roca'" in texto or "franjas" in texto:
        return "constancia"
    if "calle_mercado" in texto or "kiosco" in texto:
        return "negocio"
    return "perfeccionismo"


def categoria(datos: dict) -> str:
    """Lección del episodio, para elegir el producto."""
    g = datos.get("guion", {})
    zonas = g.get("franjas") or ([g["arriba"], g["abajo"]] if "arriba" in g else [g])
    objetos = {o.get("tipo") for z in zonas if isinstance(z, dict) for o in z.get("objetos", []) if isinstance(o, dict)}
    personajes = {p.get("tipo") for z in zonas if isinstance(z, dict) for p in z.get("personajes", [])
                  if isinstance(p, dict)}
    if "roca" in objetos:
        return "constancia"
    if "kiosco" in objetos:
        return "dinero"
    if personajes & {"martillo_hacedor", "martillo_perfeccionista"}:
        return "martillos"
    if "escalera" in objetos:
        return "escalera"
    if "silla" in objetos:
        return "silla"
    return "constancia"


def candidatos(datos: dict) -> list[str]:
    """Productos que se ven en el vídeo, del preferido al último."""
    cat = categoria(datos)
    lista = list(PRODUCTOS[cat])
    g = json.dumps(datos.get("guion", {}))
    if '"lampara"' in g:
        lista.append(LAMPARA)
    if "portatil" in g or "laptop" in g:
        lista.append(PORTATIL)
    return lista


def _candidatos_archivo(ruta: Path) -> list[str] | None:
    """Lo mismo, leyendo un episodio de la carpeta sin renderizarlo (rápido)."""
    from .plantillas import _clave, leer, normalizar

    try:
        texto = normalizar(ruta.read_text(encoding="utf-8"))
        if ruta.suffix == ".json":
            return candidatos(json.loads(texto))
        campos, _ = leer(texto)
        p = _clave(campos.get("plantilla", ""))
        if p == "construir":
            objeto = "escalera" if _clave(campos.get("objeto", "")) == "escalera" else "silla"
            return PRODUCTOS[objeto] + [LAMPARA]
        if p == "martillos":
            return PRODUCTOS["martillos"] + [LAMPARA]
        return {"roca": PRODUCTOS["constancia"], "paneles": PRODUCTOS["constancia"],
                "kioscos": PRODUCTOS["dinero"]}.get(p)
    except (OSError, ValueError, AttributeError):
        return None


def _numero_episodio(ident: str) -> int:
    import re

    m = re.match(r"ep(\d+)", ident)
    return int(m.group(1)) if m else numero(ident, "num")


def elegir_producto(opciones: list[str], ident: str, anterior: str | None) -> str:
    opciones = list(opciones)
    if opciones[:2] == PRODUCTOS["constancia"] and _numero_episodio(ident) % 2:  # mazo o libro, alternando
        opciones[0], opciones[1] = opciones[1], opciones[0]
    return next((o for o in opciones if o != anterior), opciones[0])


def producto_anterior(ruta: Path) -> str | None:
    """Producto del episodio anterior (por número) de la misma carpeta."""
    from .plantillas import _nombre, id_de_archivo

    ruta = Path(ruta)
    carpeta = ruta.parent
    num, _ = _nombre(ruta)
    if num is None or not carpeta.is_dir():
        return None
    lista = []
    for otro in list(carpeta.glob("*.json")) + list(carpeta.glob("*.txt")):
        n, _ = _nombre(otro)
        if n is not None and n < num:
            lista.append((n, otro.name, otro))
    anterior = None
    for _, _, otro in sorted(lista):
        opciones = _candidatos_archivo(otro)
        ident = id_de_archivo(otro)
        if opciones and ident:
            anterior = elegir_producto(opciones, ident, anterior)
    return anterior


def amazon() -> dict | None:
    """Tienda e ID de afiliado de config/amazon.txt (o None si no existe)."""
    try:
        campos = {}
        for linea in AMAZON.read_text(encoding="utf-8").splitlines():
            if ":" in linea and not linea.strip().startswith("#"):
                k, v = linea.split(":", 1)
                campos[k.strip().lower()] = v.strip()
        if campos.get("tienda") and campos.get("id"):
            return campos
    except OSError:
        pass
    return None


def _elige(lista: list, ident: str, sal: str, paso: int):
    """Variante para este episodio: episodios seguidos nunca repiten (paso primo con el tamaño)."""
    n = _numero_episodio(ident)
    return lista[(n * paso + numero(sal, "base")) % len(lista)]


def amazon_partes(datos: dict, anterior: str | None = None) -> dict | None:
    """Bloque de la descripción (3 líneas) y primer comentario (2 líneas), o None sin config/amazon.txt."""
    conf = amazon()
    if not conf:
        return None
    ident = datos["id"]
    cat = categoria(datos)
    producto = elegir_producto(candidatos(datos), ident, anterior)
    leccion = _elige(LECCIONES[cat], ident, "leccion", 1)
    if producto == "Atomic Habits":
        puente = _elige(PUENTES_LIBRO, ident, "puente", 3).format(l=leccion)
    else:
        puente = _elige(PUENTES, ident, "puente", 5).format(p=producto, l=leccion)
    accion = _elige(ACCIONES[cat], ident, "accion", 7)
    emoji = _elige(EMOJIS_AMAZON, ident, "emoji", 5)
    nombre = f"{producto} book" if producto == "Atomic Habits" else producto
    comentario = _elige(COMENTARIOS, ident, "comentario", 7)
    tienda = conf["tienda"].removeprefix("https://").removeprefix("www.").strip("/")
    enlace = f"https://www.{tienda}/s?k={quote_plus(producto)}&tag={conf['id']}"
    return {
        "producto": producto,
        "descripcion": f"{puente}\n{emoji} Get this {nombre} and {accion} — link in the first comment 👇\n{AVISO}",
        "comentario": f"{comentario}\n{enlace}",
    }


def _cierre_legible(cierre: str) -> str:
    if cierre.count(">") == 1:
        a, b = (x.strip() for x in cierre.split(">"))
        return f"{a} beats {b[:1].lower() + b[1:]}"
    return cierre


def generar(datos: dict, anterior: str | None = None) -> str:
    """`anterior`: producto de Amazon del episodio anterior (para no repetirlo)."""
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
    amz = amazon_partes(datos, anterior)
    bloque = f"{amz['descripcion']}\n" if amz else ""
    texto = (
        "FACEBOOK\n"
        f"{fb}\n"
        f"{' '.join(tags_fb)}\n"
        f"{bloque}"
        "\n"
        "YOUTUBE\n"
        f"Title: {titulo}\n"
        "Description:\n"
        f"{yt_desc}\n"
        f"{bloque}"
        f"Hashtags: {' '.join(tags_yt)}\n"
    )
    if amz:
        texto += f"\nPRIMER COMENTARIO\n{amz['comentario']}\n"
    return texto
