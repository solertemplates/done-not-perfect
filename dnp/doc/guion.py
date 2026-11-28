"""Guion de un caso de la serie "Money Cases" / "Casos de dinero" (estilo true crime).

Cada caso son DOS archivos en episodios_largos/:
    NN_caso_<nombre>_guion_en.txt   (inglés: texto y todo lo que se ve)
    NN_caso_<nombre>_guion_es.txt   (español: el texto; lo que se ve se toma del inglés, frase a frase)

Cabecera (inglés; el español repite titulo, expediente, ciudad, miniatura, siguiente y pregunta traducidos):

    id: caso01_mismo_sueldo
    modo: completo          # completo | prueba (solo 60 s) | borrador (no se renderiza)
    titulo: Same Salary, Different Life
    expediente: CASE 01: SAME SALARY
    ciudad: Portland, Oregon
    anio: 2014
    miniatura: SAME SALARY. DIFFERENT LIFE.
    producto: budget planner
    siguiente: CASE 02: SAME AGE
    pregunta: Two friends, same age. One car changed everything.

Secciones: == GANCHO · == CAPITULO n | TÍTULO | AÑO · == FINAL

Cada frase (bloque separado por una línea en blanco):
* texto: lo que dice la voz. Colores: {+logro} verde · {-deuda} rojo · {!riesgo} amarillo.
* voz (opcional): narrador (por defecto) o sarah (voz femenina: Sarah y momentos clave).
* clip: palabras de lo que se ve (alternativas con |). Busca primero el objeto exacto.
* objeto (opcional): el objeto que la voz nombra y que TIENE que verse (alternativas con |).
* quien: sarah, mark, pareja o nadie · lugar: casa, cocina, ciudad, oficina o tienda.
* pin (opcional): id de Pixabay fijo · grande: si (texto grande: miniganchos).
* musica (opcional): aquí empieza otra música (suspense, intriga, emotivo, epico, tension, esperanza).
* evidencia (opcional): rótulo de expediente "EVIDENCE" (facturas, extractos, notas).
* rotulo (opcional): fecha o cifra abajo a la izquierda ("MARCH 2015 · $4,300").
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
VOCES = ("narrador", "sarah")
PRODUCTOS = ("budget planner", "cash envelope wallet", "piggy bank", "Atomic Habits", "The Psychology of Money",
             "The Total Money Makeover")
CABECERA_EN = {"id", "modo", "titulo", "expediente", "ciudad", "anio", "miniatura", "producto", "siguiente",
               "pregunta"}
CABECERA_ES = {"titulo", "expediente", "ciudad", "miniatura", "siguiente", "pregunta", "anio"}
CAMPOS_EN = {"texto", "voz", "clip", "objeto", "quien", "lugar", "pin", "grande", "musica", "evidencia", "rotulo"}
CAMPOS_ES = {"texto", "voz", "evidencia", "rotulo"}
COLOR_MARCA = {"+": "verde", "-": "rojo", "!": "amarillo"}
_MARCA = re.compile(r"\{([+\-!])([^{}]+)\}")


@dataclass
class Frase:
    texto: dict  # idioma -> texto con marcas
    clip: list[str]
    quien: str = "nadie"
    lugar: str = "casa"
    objeto: list[str] = field(default_factory=list)
    pin: list[int] = field(default_factory=list)
    grande: bool = False
    seccion: int = 0
    voz: dict = field(default_factory=lambda: {"en": "narrador", "es": "narrador"})
    musica: str | None = None
    evidencia: dict = field(default_factory=dict)
    rotulo: dict = field(default_factory=dict)

    def limpio(self, idioma: str) -> str:
        return _MARCA.sub(lambda m: m.group(2), self.texto[idioma]).strip()

    def palabras(self, idioma: str) -> list[tuple[str, str | None]]:
        out = []
        pos = 0
        t = self.texto[idioma]
        for m in _MARCA.finditer(t):
            out += [(w, None) for w in t[pos:m.start()].split()]
            out += [(w, COLOR_MARCA[m.group(1)]) for w in m.group(2).split()]
            pos = m.end()
        out += [(w, None) for w in t[pos:].split()]
        juntas: list[tuple[str, str | None]] = []
        for w, c in out:  # la puntuación suelta va pegada a la palabra anterior
            if juntas and not re.search(r"\w", w):
                juntas[-1] = (juntas[-1][0] + w, juntas[-1][1])
            else:
                juntas.append((w, c))
        return juntas


@dataclass
class Seccion:
    tipo: str  # gancho, capitulo, final
    numero: int = 0
    titulo: dict = field(default_factory=dict)
    anio: str = ""
    musica: str = "emotivo"
    frases: list[Frase] = field(default_factory=list)


@dataclass
class Guion:
    id: str
    modo: str
    cabecera: dict  # idioma -> {campo: valor}
    secciones: list[Seccion]
    archivo: str = ""

    def frases(self):
        return [f for s in self.secciones for f in s.frases]

    def nombre(self, idioma: str) -> str:
        return f"{self.id}_prueba_{idioma}" if self.modo == "prueba" else f"{self.id}_{idioma}"

    def cab(self, idioma: str, campo: str, defecto: str = "") -> str:
        return self.cabecera.get(idioma, {}).get(campo) or self.cabecera["en"].get(campo, defecto)


def _clave(k: str) -> str:
    from ..plantillas import _clave as c

    return c(k)


def _bloques(texto: str):
    from ..plantillas import normalizar

    for b in re.split(r"\n\s*\n", normalizar(texto).strip()):
        lineas = [x.strip() for x in b.splitlines() if x.strip() and not x.strip().startswith("#")]
        if lineas:
            yield lineas


def _leer_uno(texto: str, idioma: str, errores: list[str]):
    """(cabecera, [(cabeza_de_sección, [campos de cada frase])]) de un archivo."""
    permitidos_cab = CABECERA_EN if idioma == "en" else CABECERA_ES
    permitidos = CAMPOS_EN if idioma == "en" else CAMPOS_ES
    cab: dict[str, str] = {}
    secciones: list[tuple[list[str], dict, list[dict]]] = []
    for lineas in _bloques(texto):
        campos: dict[str, str] = {}
        for linea in lineas:
            if linea.startswith("=="):
                secciones.append(([p.strip() for p in linea.strip("= ").split("|")], {}, []))
                continue
            if ":" not in linea:
                errores.append(f"[{idioma}] La línea \"{linea[:50]}\" no tiene \"campo: valor\".")
                continue
            k, v = linea.split(":", 1)
            campos[_clave(k)] = v.strip()
        if not campos:
            continue
        if not secciones:
            for k in campos:
                if k not in permitidos_cab:
                    sug = difflib.get_close_matches(k, sorted(permitidos_cab), n=1, cutoff=0.6)
                    errores.append(f"[{idioma}] El campo '{k}' no existe en la cabecera."
                                   + (f" ¿Querías decir '{sug[0]}'?" if sug else ""))
            cab.update(campos)
            continue
        if set(campos) == {"musica"}:
            secciones[-1][1]["musica"] = campos["musica"]
            continue
        n = sum(len(s[2]) for s in secciones) + 1
        for k in campos:
            if k not in permitidos:
                sug = difflib.get_close_matches(k, sorted(permitidos), n=1, cutoff=0.6)
                errores.append(f"[{idioma}] Frase {n}: el campo '{k}' no existe."
                               + (f" ¿Querías decir '{sug[0]}'?" if sug else ""))
        if not campos.get("texto"):
            errores.append(f"[{idioma}] Frase {n}: falta 'texto:'.")
        secciones[-1][2].append(campos)
    return cab, secciones


def leer(texto_en: str, texto_es: str, ruta: Path | str = "") -> Guion:
    ruta = Path(ruta)
    errores: list[str] = []
    cab_en, sec_en = _leer_uno(texto_en, "en", errores)
    cab_es, sec_es = _leer_uno(texto_es, "es", errores)
    if len(sec_en) != len(sec_es):
        errores.append(f"El inglés tiene {len(sec_en)} secciones y el español {len(sec_es)}: deben ser las mismas.")
    secciones: list[Seccion] = []
    for si, ((cabeza, extra, frases_en), (cabeza_es, _, frases_es)) in enumerate(zip(sec_en, sec_es)):
        tipo = _clave(cabeza[0])
        if tipo == "gancho":
            sec = Seccion("gancho", musica="suspense")
        elif tipo == "final":
            sec = Seccion("final", musica="esperanza")
        elif tipo.startswith("capitulo"):
            num = re.findall(r"\d+", cabeza[0])
            if len(cabeza) < 3 or len(cabeza_es) < 2 or not num:
                errores.append(f"Sección {si + 1}: debe ser == CAPITULO 1 | THE PROMISE | 1 (en español, "
                               "== CAPITULO 1 | LA PROMESA | 1).")
                continue
            sec = Seccion("capitulo", int(num[0]), {"en": cabeza[1], "es": cabeza_es[1]}, anio=cabeza[-1])
        else:
            errores.append(f"Sección desconocida \"{' | '.join(cabeza)}\". Usa == GANCHO, == CAPITULO n | ... o == FINAL.")
            continue
        if "musica" in extra:
            sec.musica = extra["musica"]
        if sec.musica not in MUSICAS:
            errores.append(f"Sección {si + 1}: 'musica' debe ser una de: {', '.join(MUSICAS)}.")
        if len(frases_en) != len(frases_es):
            errores.append(f"Sección {si + 1}: el inglés tiene {len(frases_en)} frases y el español {len(frases_es)}. "
                           "Tienen que ir frase a frase.")
        for fi, (c, ce) in enumerate(zip(frases_en, frases_es)):
            n = f"Sección {si + 1}, frase {fi + 1}"
            if not c.get("clip"):
                errores.append(f"{n}: falta 'clip:' (palabras de lo que se ve).")
            quien = _clave(c.get("quien", "nadie"))
            lugar = _clave(c.get("lugar", "casa"))
            if quien not in QUIEN:
                errores.append(f"{n}: 'quien' debe ser {', '.join(QUIEN)}.")
            if lugar not in LUGARES:
                errores.append(f"{n}: 'lugar' debe ser {', '.join(LUGARES)}.")
            voz = {"en": _clave(c.get("voz", "narrador")), "es": _clave(ce.get("voz") or c.get("voz", "narrador"))}
            if any(v not in VOCES for v in voz.values()):
                errores.append(f"{n}: 'voz' debe ser narrador o sarah.")
            musica = c.get("musica")
            if musica and musica not in MUSICAS:
                errores.append(f"{n}: 'musica' debe ser una de: {', '.join(MUSICAS)}.")
            sec.frases.append(Frase(
                texto={"en": c.get("texto", ""), "es": ce.get("texto", "")},
                clip=[x.strip() for x in c.get("clip", "").split("|") if x.strip()],
                quien=quien, lugar=lugar,
                objeto=[x.strip().lower() for x in c.get("objeto", "").split("|") if x.strip()],
                pin=[int(x) for x in re.findall(r"\d+", c.get("pin", ""))],
                grande=_clave(c.get("grande", "no")) in ("si", "yes", "true"),
                seccion=len(secciones), voz=voz, musica=musica,
                evidencia={k: v for k, v in (("en", c.get("evidencia")), ("es", ce.get("evidencia") or c.get("evidencia"))) if v},
                rotulo={k: v for k, v in (("en", c.get("rotulo")), ("es", ce.get("rotulo") or c.get("rotulo"))) if v},
            ))
        secciones.append(sec)
    ident = cab_en.get("id") or ""
    if not re.fullmatch(r"[a-z0-9_]{3,60}", ident):
        errores.append("Falta 'id:' en la cabecera del inglés (por ejemplo id: caso01_mismo_sueldo).")
    modo = cab_en.get("modo", "prueba")
    if modo not in ("prueba", "completo", "borrador"):
        errores.append("'modo' debe ser prueba, completo o borrador.")
    if cab_en.get("producto") and cab_en["producto"] not in PRODUCTOS:
        errores.append(f"'producto' debe ser uno de: {', '.join(PRODUCTOS)}.")
    if not secciones or secciones[0].tipo != "gancho":
        errores.append("El guion tiene que empezar por == GANCHO.")
    if errores:
        raise ErrorConfig(errores, str(ruta))
    return Guion(ident, modo, {"en": cab_en, "es": cab_es}, secciones, str(ruta))


def pareja(ruta: Path) -> tuple[Path, Path]:
    """(inglés, español) de un caso a partir de cualquiera de sus dos archivos."""
    ruta = Path(ruta)
    base = re.sub(r"_(en|es)$", "", ruta.stem)
    return ruta.with_name(f"{base}_en.txt"), ruta.with_name(f"{base}_es.txt")


def cargar(ruta) -> Guion:
    en, es = pareja(Path(ruta))
    faltan = [str(p) for p in (en, es) if not p.exists()]
    if faltan:
        raise ErrorConfig([f"Falta el archivo '{f}' (cada caso lleva su guion en inglés y en español)." for f in faltan],
                          str(ruta))
    return leer(en.read_text(encoding="utf-8"), es.read_text(encoding="utf-8"), en)
