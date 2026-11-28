"""Guion de un capítulo largo (.txt en episodios_largos/), en inglés y español a la vez.

Formato (bloques separados por una línea en blanco):

    id: largo01
    modo: prueba              # prueba = 60 s (gancho + inicio del capítulo 1); completo = todo
    titulo_en: Same Salary, Different Life
    titulo_es: Mismo sueldo, otra vida
    miniatura_en: SAME SALARY. DIFFERENT LIFE.
    miniatura_es: MISMO SUELDO. OTRA VIDA.
    producto: budget planner

    == GANCHO
    musica: suspense

    en: Same salary. Same city.
    es: Mismo sueldo. Misma ciudad.
    clip: city aerial drone | skyline aerial
    quien: nadie

    == CAPITULO 1 | THE PROMISE | LA PROMESA | 1
    musica: emotivo
    ...

Cada frase lleva:
* en / es: lo que dice la voz. Palabras clave en color: {+libre} verde, {-deuda} rojo, {!riesgo} amarillo.
* clip: palabras para buscar el vídeo (alternativas separadas por |), de lo que se VE en esa frase.
* quien: sarah, mark, pareja o nadie (continuidad de personajes).
* lugar (opcional): casa, cocina, ciudad, oficina o tienda (plano neutro si no hay clip que encaje).
* pin (opcional): id(s) de Pixabay fijos para esa frase.
* grande (opcional, sí/no): además, texto grande en pantalla (miniganchos).
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..config import ErrorConfig

IDIOMAS = ("en", "es")
QUIEN = ("sarah", "mark", "pareja", "nadie")
LUGARES = ("casa", "cocina", "ciudad", "oficina", "tienda")
MUSICAS = ("suspense", "emotivo", "epico", "tension", "esperanza", "intriga")
PRODUCTOS = ("budget planner", "cash envelope wallet", "piggy bank", "Atomic Habits", "The Psychology of Money",
             "The Total Money Makeover")
CABECERA = {"id", "modo", "titulo_en", "titulo_es", "miniatura_en", "miniatura_es", "producto",
            "siguiente_en", "siguiente_es", "pregunta_en", "pregunta_es"}
CAMPOS_FRASE = {"en", "es", "clip", "quien", "lugar", "pin", "grande"}
COLOR_MARCA = {"+": "verde", "-": "rojo", "!": "amarillo"}
_MARCA = re.compile(r"\{([+\-!])([^{}]+)\}")


@dataclass
class Frase:
    texto: dict  # idioma -> texto con marcas {+...}
    clip: list[str]
    quien: str = "nadie"
    lugar: str = "casa"
    pin: list[int] = field(default_factory=list)
    grande: bool = False
    seccion: int = 0

    def limpio(self, idioma: str) -> str:
        """Texto para la voz (sin marcas de color)."""
        return _MARCA.sub(lambda m: m.group(2), self.texto[idioma]).strip()

    def palabras(self, idioma: str) -> list[tuple[str, str | None]]:
        """[(palabra, color o None)] en orden, para los subtítulos."""
        out = []
        pos = 0
        t = self.texto[idioma]
        for m in _MARCA.finditer(t):
            out += [(w, None) for w in t[pos:m.start()].split()]
            out += [(w, COLOR_MARCA[m.group(1)]) for w in m.group(2).split()]
            pos = m.end()
        out += [(w, None) for w in t[pos:].split()]
        juntas: list[tuple[str, str | None]] = []
        for w, c in out:  # la puntuación suelta ("…", "!") va pegada a la palabra anterior
            if juntas and not re.search(r"\w", w):
                juntas[-1] = (juntas[-1][0] + w, juntas[-1][1])
            else:
                juntas.append((w, c))
        return juntas


@dataclass
class Seccion:
    tipo: str  # gancho, capitulo, final
    numero: int = 0
    titulo: dict = field(default_factory=dict)  # idioma -> título del capítulo
    anio: str = ""
    musica: str = "emotivo"
    frases: list[Frase] = field(default_factory=list)


@dataclass
class Guion:
    id: str
    modo: str
    cabecera: dict
    secciones: list[Seccion]
    archivo: str = ""

    def frases(self):
        return [f for s in self.secciones for f in s.frases]

    def nombre(self, idioma: str) -> str:
        return f"{self.id}_prueba_{idioma}" if self.modo == "prueba" else f"{self.id}_{idioma}"


def _clave(k: str) -> str:
    from ..plantillas import _clave as c

    return c(k)


def leer(texto: str, ruta: Path | str = "") -> Guion:
    from ..plantillas import normalizar

    ruta = Path(ruta)
    errores: list[str] = []
    cab: dict[str, str] = {}
    secciones: list[Seccion] = []
    bloques = re.split(r"\n\s*\n", normalizar(texto).strip())
    for b in bloques:
        lineas = [x.strip() for x in b.splitlines() if x.strip() and not x.strip().startswith("#")]
        if not lineas:
            continue
        campos: dict[str, str] = {}
        for linea in lineas:
            if linea.startswith("=="):
                partes = [p.strip() for p in linea.strip("= ").split("|")]
                cabeza = _clave(partes[0])
                if cabeza == "gancho":
                    secciones.append(Seccion("gancho", musica="suspense"))
                elif cabeza == "final":
                    secciones.append(Seccion("final", musica="esperanza"))
                elif cabeza.startswith("capitulo"):
                    n = re.findall(r"\d+", partes[0])
                    if len(partes) < 4 or not n:
                        errores.append(f"La línea \"{linea}\" debe ser: == CAPITULO 1 | THE PROMISE | LA PROMESA | 1")
                        continue
                    secciones.append(Seccion("capitulo", int(n[0]), {"en": partes[1], "es": partes[2]},
                                             anio=partes[3]))
                else:
                    errores.append(f"Sección desconocida \"{linea}\". Usa == GANCHO, == CAPITULO n | ... o == FINAL.")
                continue
            if ":" not in linea:
                errores.append(f"La línea \"{linea[:50]}\" no tiene \"campo: valor\".")
                continue
            k, v = linea.split(":", 1)
            campos[_clave(k)] = v.strip()
        if not campos:
            continue
        if not secciones:  # cabecera
            for k, v in campos.items():
                if k not in CABECERA:
                    sug = difflib.get_close_matches(k, sorted(CABECERA), n=1, cutoff=0.6)
                    errores.append(f"El campo '{k}' no existe." + (f" ¿Querías decir '{sug[0]}'?" if sug else ""))
                cab[k] = v
            continue
        sec = secciones[-1]
        if set(campos) == {"musica"}:
            if campos["musica"] not in MUSICAS:
                errores.append(f"'musica' debe ser una de: {', '.join(MUSICAS)}. Ahora vale \"{campos['musica']}\".")
            sec.musica = campos["musica"]
            continue
        n_frase = len([f for s in secciones for f in s.frases]) + 1
        for k in campos:
            if k not in CAMPOS_FRASE | {"musica"}:
                sug = difflib.get_close_matches(k, sorted(CAMPOS_FRASE), n=1, cutoff=0.6)
                errores.append(f"Frase {n_frase}: el campo '{k}' no existe." + (f" ¿Querías decir '{sug[0]}'?" if sug else ""))
        for idioma in IDIOMAS:
            if not campos.get(idioma):
                errores.append(f"Frase {n_frase}: falta '{idioma}:'.")
        if not campos.get("clip"):
            errores.append(f"Frase {n_frase}: falta 'clip:' (palabras de lo que se ve).")
        quien = _clave(campos.get("quien", "nadie"))
        if quien not in QUIEN:
            errores.append(f"Frase {n_frase}: 'quien' debe ser {', '.join(QUIEN)}.")
        lugar = _clave(campos.get("lugar", "casa"))
        if lugar not in LUGARES:
            errores.append(f"Frase {n_frase}: 'lugar' debe ser {', '.join(LUGARES)}.")
        if "musica" in campos:
            sec.musica = campos["musica"]
        pins = [int(x) for x in re.findall(r"\d+", campos.get("pin", ""))]
        sec.frases.append(Frase({i: campos.get(i, "") for i in IDIOMAS},
                                [c.strip() for c in campos.get("clip", "").split("|") if c.strip()],
                                quien, lugar, pins, _clave(campos.get("grande", "no")) in ("si", "yes", "true"),
                                len(secciones) - 1))
    ident = cab.get("id") or re.sub(r"^(\d+).*", r"largo\1", ruta.stem)
    if not re.fullmatch(r"[a-z0-9_]{3,40}", ident or ""):
        errores.append("Falta 'id:' (por ejemplo id: largo01).")
    modo = cab.get("modo", "prueba")
    if modo not in ("prueba", "completo"):
        errores.append("'modo' debe ser prueba o completo.")
    if cab.get("producto") and cab["producto"] not in PRODUCTOS:
        errores.append(f"'producto' debe ser uno de: {', '.join(PRODUCTOS)}.")
    if not any(s.tipo == "gancho" for s in secciones):
        errores.append("Falta la sección == GANCHO.")
    if errores:
        raise ErrorConfig(errores, str(ruta))
    return Guion(ident, modo, cab, secciones, str(ruta))


def cargar(ruta) -> Guion:
    ruta = Path(ruta)
    if not ruta.exists():
        raise ErrorConfig([f"No existe el archivo '{ruta}'."], str(ruta))
    return leer(ruta.read_text(encoding="utf-8"), ruta)
