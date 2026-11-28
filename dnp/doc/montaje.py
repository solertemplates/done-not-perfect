"""Montaje del vídeo largo estilo documental.

1. Voz: cada frase se sintetiza (con el tiempo de cada palabra).
2. Clips: cada frase se parte en trozos de 3-5 s y cada trozo lleva un clip distinto que
   muestra lo que dice la voz (los mismos clips en inglés y en español).
3. Cada trozo se etaloniza igual (balance de blancos y brillo normalizados + la misma LUT de
   cine, cálida y contrastada) y lleva un movimiento suave de cámara (zoom lento, a velocidad normal).
4. Encima: subtítulos grandes palabra a palabra (palabras clave en verde/rojo/amarillo), títulos
   de capítulo estilo película, franjas finas de cine, viñeta suave y grano ligero.
5. Audio: voz + música real (más baja que la voz y aún más mientras habla).
"""
from __future__ import annotations

import json
import math
import multiprocessing as mp
import os
import random
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .clips import Buscador, sondear
from .guion import Guion
from .musica import Discoteca
from .voz import OBJETIVO_PPM, PAUSA, SR, Narrador

ANCHO, ALTO, FPS = 1920, 1080, 30
MARGEN = 1.10  # el clip se decodifica un 10 % más grande para poder moverse sin bordes
PAUSA_CAPITULO = 2.6  # silencio de voz (solo música) para el título del capítulo
DUR_PRUEBA = 60.0
FRANJA = 40  # franjas de cine arriba y abajo (px)
COLORES_ASS = {"verde": "&H6EFF3C&", "rojo": "&H3C28FF&", "amarillo": "&H00D6FF&"}
TEXTOS = {
    "en": {"capitulo": "CHAPTER", "anio": "YEAR", "sigue": "To be continued…", "evidencia": "EVIDENCE",
           "siguiente": "NEXT CASE"},
    "es": {"capitulo": "CAPÍTULO", "anio": "AÑO", "sigue": "Continuará…", "evidencia": "EVIDENCIA",
           "siguiente": "PRÓXIMO CASO"},
}


# ================================================================== COLOR
def curva_cine() -> np.ndarray:
    """LUT de cine (la misma en todo el vídeo): contraste en S, negros algo levantados,
    altas luces cálidas y sombras ligeramente frías. Devuelve 3 tablas de 256 valores."""
    x = np.linspace(0, 1, 256)
    s = x + 0.38 * (x * x * (3 - 2 * x) - x)  # curva en S: más contraste en los medios
    s = np.clip(0.035 + 0.95 * s, 0, 1)  # negros algo levantados (aspecto de cine)
    r = np.clip(s + 0.045 * x ** 1.5, 0, 1)
    g = np.clip(s + 0.012 * x, 0, 1)
    b = np.clip(s - 0.05 * x ** 1.2 + 0.025 * (1 - x) ** 2, 0, 1)
    return np.stack([r, g, b])


CINE = curva_cine()


def tablas_clip(muestra: np.ndarray) -> list[np.ndarray]:
    """Tablas (una por canal) que normalizan el clip y aplican la LUT de cine.

    * balance de blancos: 60 % del 'mundo gris' (los canales se acercan a su media común);
    * brillo y contraste: la luminancia media va a 0,46 y la desviación a 0,22 (con límites).
    """
    m = muestra.reshape(-1, 3).astype(np.float32) / 255
    medias = m.mean(0) + 1e-4
    gris = medias.mean()
    wb = 1 + 0.6 * (gris / medias - 1)
    luma = (m * wb) @ np.array([0.2126, 0.7152, 0.0722])
    mu, sd = float(luma.mean()), float(luma.std()) + 1e-4
    k = float(np.clip(0.22 / sd, 0.8, 1.45))
    x = np.linspace(0, 1, 256)
    tablas = []
    for c in range(3):
        v = np.clip((x * wb[c] - mu) * k + 0.46, 0, 1)
        tablas.append(np.clip(np.interp(v, np.linspace(0, 1, 256), CINE[c]) * 255 + 0.5, 0, 255).astype(np.uint8))
    return tablas


def etalonar(img: np.ndarray, tablas) -> np.ndarray:
    try:
        import cv2

        return cv2.LUT(img, np.stack(tablas, axis=-1).reshape(256, 1, 3))
    except ImportError:
        pass
    out = np.empty_like(img)
    for c in range(3):
        out[..., c] = np.take(tablas[c], img[..., c])
    return out


# ================================================================== LÍNEA DE TIEMPO
@dataclass
class Trozo:
    inicio: float
    dur: float
    frase: int  # índice de la frase
    n: int  # número de trozo dentro de la frase


@dataclass
class Linea:
    idioma: str
    frases: list  # (frase, locucion, inicio)
    trozos: list[Trozo]
    titulos: list  # (inicio, texto1, texto2): títulos de capítulo
    duracion: float
    secciones: list  # (inicio, ambiente): cada entrada empieza una música nueva (como mucho 20 s)
    tarjetas: list = None  # (inicio, duración, tipo, [líneas]): expediente del caso y "siguiente caso"
    evidencias: list = None  # (inicio, duración, texto)
    rotulos: list = None  # (inicio, duración, texto)


MAX_MUSICA = 20.0  # ninguna música dura más de 20 s
PAUSA_CASO = 3.2  # tiempo (solo música) para el rótulo del expediente antes del capítulo 1


def partir(span: float) -> list[float]:
    n = max(1, math.ceil(span / 5.0))
    if span / n < 2.5 and n > 1 and span / (n - 1) <= 5.0:
        n -= 1
    return [span / n] * n


def _cues(inicios_seccion, frases_t, fin) -> list[tuple[float, str]]:
    """Músicas: empiezan en cada sección y donde el guion pone 'musica'; si una pasaría de 20 s,
    se cambia en la frase (escena) más cercana antes de llegar a los 20 s."""
    marcas = sorted(set(inicios_seccion) | {(t, m) for t, m in frases_t if m})
    cues: list[tuple[float, str]] = []
    for t, m in marcas:
        if cues and abs(cues[-1][0] - t) < 0.01:
            cues[-1] = (t, m)
        else:
            cues.append((t, m))
    escenas = sorted({t for t, _ in frases_t})
    out: list[tuple[float, str]] = []
    for k, (t, m) in enumerate(cues):
        t1 = cues[k + 1][0] if k + 1 < len(cues) else fin
        out.append((t, m))
        actual = t
        while t1 - actual > MAX_MUSICA:
            corte = max([e for e in escenas if actual + 6 <= e <= actual + MAX_MUSICA] or [actual + MAX_MUSICA])
            out.append((corte, m))
            actual = corte
    return out


def linea_de_tiempo(g: Guion, idioma: str, narradores, hasta: float | None) -> Linea:
    """`narradores`: {papel: Narrador} (narrador y sarah) o un solo Narrador para todo."""
    if not isinstance(narradores, dict):
        narradores = {"narrador": narradores, "sarah": narradores}
    t = 0.0
    frases, trozos, titulos, tarjetas, evidencias, rotulos = [], [], [], [], [], []
    inicios, marcas_frase = [], []
    todas = g.frases()
    tx = TEXTOS[idioma]
    n_evidencia = 0

    def cerrar(fin):
        ln = Linea(idioma, frases, trozos, titulos, fin, [], tarjetas, evidencias, rotulos)
        ln.secciones = _cues(inicios, marcas_frase, fin)
        return ln

    for si, sec in enumerate(g.secciones):
        inicios.append((t, sec.musica))
        for fi, f in enumerate(sec.frases):
            loc = narradores[f.voz[idioma]].decir(f.limpio(idioma))
            extra = 0.0
            if fi == 0 and sec.tipo == "capitulo":
                if sec.numero == min(s.numero for s in g.secciones if s.tipo == "capitulo"):
                    lineas = [g.cab(idioma, "expediente", g.id.upper()),
                              " · ".join(x for x in (g.cab(idioma, "ciudad"), g.cab(idioma, "anio")) if x)]
                    tarjetas.append((t, PAUSA_CASO, "caso", lineas))
                    extra += PAUSA_CASO
                titulos.append((t + extra, f"{tx['capitulo']} {sec.numero}: {sec.titulo[idioma].upper()}",
                                f"{tx['anio']} {sec.anio}"))
                extra += PAUSA_CAPITULO
            span = extra + loc.duracion + PAUSA
            if hasta is not None and t + span > hasta - 0.2:
                return _rellenar(cerrar(hasta), t, todas)
            ini = t + extra
            frases.append((f, loc, ini))
            marcas_frase.append((t, f.musica))
            if f.evidencia.get(idioma):
                n_evidencia += 1
                evidencias.append((ini, loc.duracion + PAUSA, f"{tx['evidencia']} #{n_evidencia:02d} · "
                                                              f"{f.evidencia[idioma].upper()}"))
            if f.rotulo.get(idioma):
                rotulos.append((ini, loc.duracion + PAUSA, f.rotulo[idioma].upper()))
            for k, d in enumerate(partir(span)):
                trozos.append(Trozo(t + sum(partir(span)[:k]), d, todas.index(f), k))
            t += span
        if sec.tipo == "final" and hasta is None:
            sig = g.cab(idioma, "siguiente")
            if sig:  # "Siguiente caso" al final, con la música de cierre
                tarjetas.append((t, 4.5, "siguiente", [tx["siguiente"], sig.upper()]))
                trozos.append(Trozo(t, 4.5, todas.index(sec.frases[-1]), len(partir(span))))
                t += 4.5
    if hasta is not None:
        return _rellenar(cerrar(hasta), t, todas)
    return cerrar(t + 1.0)


def _rellenar(ln: Linea, t: float, todas) -> Linea:
    """Prueba de duración fija: lo que sobra hasta el final son planos nuevos de la última frase."""
    if t < ln.duracion - 1e-3 and ln.frases:
        fi = todas.index(ln.frases[-1][0])
        resto = ln.duracion - t
        if resto < 1.5 and ln.trozos:  # poco: se alarga el último plano
            ln.trozos[-1].dur += resto
            return ln
        n0 = len([x for x in ln.trozos if x.frase == fi])
        for j, d in enumerate(partir(resto)):
            ln.trozos.append(Trozo(t + j * d, d, fi, n0 + j))
    return ln


# ================================================================== VÍDEO
def _render_trozo(args):
    ruta, desde, dur, salida, semilla, n = args
    rnd = random.Random(semilla)
    w, h = int(ANCHO * MARGEN) // 2 * 2, int(ALTO * MARGEN) // 2 * 2
    muestra = _leer(ruta, desde + dur / 2, w // 4, h // 4, 1)
    tablas = tablas_clip(muestra[0])
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{desde:.3f}", "-i", str(ruta), "-t", f"{dur + 0.5:.3f}", "-an", "-vf",
           f"fps={FPS},scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    lector = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                            f"{ANCHO}x{ALTO}", "-framerate", str(FPS), "-i", "-", "-c:v", "libx264", "-preset",
                            "ultrafast", "-crf", "10", "-pix_fmt", "yuv420p", str(salida)], stdin=subprocess.PIPE)
    acerca = rnd.random() < 0.6
    z0, z1 = (1.0, 1.065) if acerca else (1.065, 1.0)
    px, py = rnd.uniform(-1, 1), rnd.uniform(-0.6, 0.6)
    ultimo = None
    for i in range(n):
        datos = lector.stdout.read(w * h * 3)
        if len(datos) == w * h * 3:
            ultimo = np.frombuffer(datos, np.uint8).reshape(h, w, 3)
        if ultimo is None:
            raise RuntimeError(f"No se pudo leer {ruta}")
        u = i / max(1, n - 1)
        u = u * u * (3 - 2 * u) * 0.7 + u * 0.3  # suave al empezar y al acabar
        z = z0 + (z1 - z0) * u
        vw, vh = w / MARGEN / z, h / MARGEN / z  # parte visible (en píxeles del clip)
        cx = w / 2 + px * (w - vw) / 2 * (0.3 + 0.7 * u)
        cy = h / 2 + py * (h - vh) / 2 * (0.3 + 0.7 * u)
        img = encuadre(ultimo, cx, cy, vw, vh)
        enc.stdin.write(etalonar(img, tablas).tobytes())
    lector.kill()
    enc.stdin.close()
    if enc.wait() != 0:
        raise RuntimeError(f"ffmpeg falló con el trozo {salida.name}")
    return str(salida)


def encuadre(src: np.ndarray, cx, cy, vw, vh) -> np.ndarray:
    """Recorte subpíxel (para que el movimiento sea suave) escalado a 1920x1080."""
    try:
        import cv2

        sx, sy = ANCHO / vw, ALTO / vh
        m = np.array([[sx, 0, -(cx - vw / 2) * sx], [0, sy, -(cy - vh / 2) * sy]], np.float32)
        return cv2.warpAffine(src, m, (ANCHO, ALTO), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    except ImportError:
        img = Image.fromarray(src).transform((ANCHO, ALTO), Image.Transform.EXTENT,
                                             (cx - vw / 2, cy - vh / 2, cx + vw / 2, cy + vh / 2),
                                             resample=Image.Resampling.BILINEAR)
        return np.asarray(img)


def _leer(ruta, seg, w, h, n):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, seg):.2f}", "-i", str(ruta), "-frames:v", str(n),
                        "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}", "-f", "rawvideo",
                        "-pix_fmt", "rgb24", "-"], capture_output=True)
    k = len(r.stdout) // (w * h * 3)
    if k == 0:
        raise RuntimeError(f"No se pudo leer {ruta}")
    return np.frombuffer(r.stdout[: k * w * h * 3], np.uint8).reshape(k, h, w, 3)


# ================================================================== SUBTÍTULOS (ASS)
def _t(s: float) -> str:
    s = max(0.0, s)
    return f"{int(s // 3600)}:{int(s % 3600 // 60):02d}:{s % 60:05.2f}"


def _limpiar(w: str) -> str:
    return w.replace("{", "").replace("}", "").replace("\\", "")


def subtitulos(linea: Linea, fuente: str, fina: str | None = None) -> str:
    """Subtítulos ASS: grupos de hasta 4 palabras; la palabra que suena se ilumina y crece."""
    cab = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {ANCHO}
PlayResY: {ALTO}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{fuente},82,&H00FFFFFF,&H00FFFFFF,&H00101010,&H96000000,-1,0,0,0,100,100,1,0,1,4.5,2,2,120,120,{FRANJA + 70},1
Style: Grande,{fuente},84,&H00FFFFFF,&H00FFFFFF,&H00101010,&H96000000,-1,0,0,0,100,100,2,0,1,5,3,5,160,160,0,1
Style: Titulo,{fina},74,&H00FFFFFF,&H00FFFFFF,&H00101010,&H78000000,0,0,0,0,100,100,16,0,1,1.2,2,5,100,100,0,1
Style: Anio,{fina},42,&H0073C8FF,&H0073C8FF,&H00101010,&H78000000,0,0,0,0,100,100,22,0,1,1,1.5,5,100,100,0,1
Style: Caso,{fina},86,&H00FFFFFF,&H00FFFFFF,&H00101010,&H78000000,0,0,0,0,100,100,14,0,1,1.2,2,5,100,100,0,1
Style: Evidencia,{fina},34,&H00FFFFFF,&H00FFFFFF,&H003C28FF,&H96000000,0,0,0,0,100,100,8,0,3,6,0,7,90,90,90,1
Style: Rotulo,{fina},38,&H0073C8FF,&H0073C8FF,&H00101010,&H96000000,0,0,0,0,100,100,10,0,1,1.2,1.5,1,90,90,{FRANJA + 60},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    fina = fina or fuente
    ev = []
    for ini, dur, tipo, lineas in linea.tarjetas or []:
        fin = ini + dur
        ev.append(f"Dialogue: 2,{_t(ini + 0.2)},{_t(fin)},Caso,,0,0,0,,{{\\fad(500,500)\\pos({ANCHO // 2},{ALTO // 2 - 30})}}"
                  f"{_limpiar(lineas[0])}")
        if len(lineas) > 1 and lineas[1]:
            ev.append(f"Dialogue: 2,{_t(ini + 0.7)},{_t(fin)},Anio,,0,0,0,,{{\\fad(500,500)\\pos({ANCHO // 2},{ALTO // 2 + 60})}}"
                      f"{_limpiar(lineas[1])}")
    for ini, dur, texto in linea.evidencias or []:
        ev.append(f"Dialogue: 2,{_t(ini)},{_t(ini + dur)},Evidencia,,0,0,0,,{{\\fad(250,250)}}{_limpiar(texto)}")
    for ini, dur, texto in linea.rotulos or []:
        ev.append(f"Dialogue: 2,{_t(ini)},{_t(ini + dur)},Rotulo,,0,0,0,,{{\\fad(300,300)}}{_limpiar(texto)}")
    for ini, t1, t2 in linea.titulos:
        fin = ini + PAUSA_CAPITULO + 0.4
        ev.append(f"Dialogue: 2,{_t(ini + 0.15)},{_t(fin)},Titulo,,0,0,0,,{{\\fad(450,450)\\pos({ANCHO // 2},{ALTO // 2 - 40})}}{t1}")
        ev.append(f"Dialogue: 2,{_t(ini + 0.55)},{_t(fin)},Anio,,0,0,0,,{{\\fad(450,450)\\pos({ANCHO // 2},{ALTO // 2 + 55})}}{t2}")
    for f, loc, ini in linea.frases:
        palabras = f.palabras(linea.idioma)
        tiempos = loc.palabras
        if len(tiempos) != len(palabras):  # Edge no siempre parte igual (números, guiones): se reparte
            from .voz import repartir

            tiempos = repartir(" ".join(w for w, _ in palabras), loc.duracion)
        if f.grande:
            texto = " ".join(_colorear(w.upper(), c) for w, c in palabras)
            ev.append(f"Dialogue: 1,{_t(ini)},{_t(ini + loc.duracion + 0.4)},Grande,,0,0,0,,{{\\q0\\fad(250,300)}}{texto}")
            continue
        grupos, actual = [], []
        for k, (w, c) in enumerate(palabras):
            actual.append(k)
            if len(actual) >= 4 or w[-1:] in ".,!?…;:":
                grupos.append(actual)
                actual = []
        if actual:
            grupos.append(actual)
        for gi, g in enumerate(grupos):
            fin_grupo = ini + (tiempos[grupos[gi + 1][0]][1] if gi + 1 < len(grupos) else tiempos[g[-1]][2] + 0.25)
            for k in g:
                a = ini + tiempos[k][1]
                b = ini + tiempos[k + 1][1] if k != g[-1] else fin_grupo  # nunca se solapan dos líneas
                partes = []
                for j in g:
                    w, c = palabras[j]
                    w = _limpiar(w)
                    if j == k:
                        partes.append(f"{{\\fscx112\\fscy112\\c{COLORES_ASS.get(c, '&H00FFFFFF&')}}}{w}{{\\r}}")
                    else:
                        base = COLORES_ASS.get(c, "&H00E6E6E6&")
                        partes.append(f"{{\\c{base}\\alpha&H30&}}{w}{{\\r}}")
                ev.append(f"Dialogue: 0,{_t(a)},{_t(max(b, a + 0.08))},Sub,,0,0,0,,{' '.join(partes)}")
    return cab + "\n".join(ev) + "\n"


def _colorear(w, c):
    w = _limpiar(w)
    return f"{{\\c{COLORES_ASS[c]}}}{w}{{\\r}}" if c else w


# ================================================================== AUDIO
# Volumen de cada ambiente (el suspense del gancho, igual que en la prueba aprobada; el piano, más bajo).
GANANCIA_MUSICA = {"suspense": 1.0, "intriga": 0.85, "tension": 0.8, "epico": 0.7, "emotivo": 0.45, "esperanza": 0.55}
SUELO = 0.06  # durante el respiro entre músicas queda un fondo muy bajo (nunca silencio total)
SALIDA, RESPIRO, ENTRADA = 2.6, 0.8, 2.2  # segundos: la anterior se apaga, respiro, la siguiente entra


def envolvente_musica(t: np.ndarray, t0: float, t1: float, primera: bool, ultima: bool) -> np.ndarray:
    """Volumen de una música de t0 a t1: entra suave, se apaga despacio, respiro casi sin música."""
    e = np.ones_like(t)
    if not primera:
        u = np.clip((t - t0) / ENTRADA, 0, 1)
        e *= u * u * (3 - 2 * u)
    if not ultima:
        u = np.clip((t - (t1 - SALIDA)) / (SALIDA - RESPIRO), 0, 1)  # baja hasta el suelo
        baja = 1 - (1 - SUELO) * (u * u * (3 - 2 * u))
        cola = np.clip(1 - (t - t1) / 0.4, 0, 1)  # el suelo se va en 0,4 s cuando ya entra la siguiente
        e *= np.where(t < t1, baja, SUELO * cola)
    return e


def mezcla(linea: Linea, discoteca: Discoteca, musicas_previas: dict) -> tuple[np.ndarray, list[str]]:
    from .musica import ajustar

    n = int(round(linea.duracion * SR))
    voz = np.zeros(n, np.float32)
    for f, loc, ini in linea.frases:
        i0 = int(ini * SR)
        a = loc.audio[: max(0, n - i0)]
        voz[i0:i0 + len(a)] += a
    pico = np.max(np.abs(voz)) + 1e-6
    voz = voz / pico * 0.85
    musica = np.zeros((n, 2), np.float32)
    titulos = []
    cues = [c for c in linea.secciones if c[0] < linea.duracion]
    anterior = None
    for k, (t0, ambiente) in enumerate(cues):
        t1 = min(cues[k + 1][0] if k + 1 < len(cues) else linea.duracion, linea.duracion)
        ultima = k == len(cues) - 1
        fin = linea.duracion if ultima else min(linea.duracion, t1 + 0.4)
        clave = (k, ambiente)
        if clave not in musicas_previas:  # la misma canción en los dos idiomas
            musicas_previas[clave] = discoteca.cancion(ambiente, evitar=anterior)
        cruda, titulo = musicas_previas[clave]
        anterior = titulo
        dur = fin - t0
        desde = int((hash((titulo, k)) % 1000) / 1000 * max(0, len(cruda) / SR - dur - 5) * SR)  # otra parte si se repite
        trozo = ajustar(cruda[desde:], dur)
        t = t0 + np.arange(len(trozo)) / SR
        trozo = trozo * (envolvente_musica(t, t0, t1, k == 0, ultima) * GANANCIA_MUSICA.get(ambiente, 0.8))[:, None]
        i0 = int(round(t0 * SR))
        musica[i0:i0 + len(trozo)] += trozo[: n - i0]
        titulos.append(titulo)
    # La música baja mientras habla la voz (la voz siempre por encima).
    habla = np.convolve((np.abs(voz) > 0.02).astype(np.float32), np.ones(int(0.35 * SR)) / int(0.35 * SR), "same")
    habla = np.clip(habla * 3, 0, 1)
    ganancia = 0.85 - 0.5 * habla
    final_fade = np.clip((linea.duracion - np.arange(n) / SR) / 1.5, 0, 1)
    pista = musica * (ganancia * final_fade)[:, None] + voz[:, None]
    pista = np.tanh(pista * 1.1) / np.tanh(1.1) * 0.78  # ≈ -14 LUFS, el nivel de YouTube
    return pista.astype(np.float32), list(dict.fromkeys(titulos))


# ================================================================== FUENTES
def fuente_fina() -> str:
    """Letra fina y moderna para títulos y rótulos (estilo documental): Montserrat Light."""
    r = subprocess.run(["fc-match", "-f", "%{family}|%{style}", "Montserrat:style=Light"], capture_output=True, text=True)
    return "Montserrat Light" if "montserrat" in r.stdout.lower() else "DejaVu Sans"


def fuente(estilo: str = "ExtraBold") -> tuple[str, str]:
    """(nombre para ASS, archivo .ttf) de Montserrat; si no está instalada, DejaVu Sans Bold."""
    for nombre in ("Montserrat", "DejaVu Sans"):
        r = subprocess.run(["fc-match", "-f", "%{family}|%{file}", f"{nombre}:style={estilo}"], capture_output=True,
                           text=True)
        fam, _, archivo = r.stdout.partition("|")
        if nombre.lower() in fam.lower() and archivo:
            return nombre, archivo
    return "DejaVu Sans", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


# ================================================================== TODO JUNTO
DUR_OBJETIVO = 540.0  # vídeo completo: unos 9 minutos


def objetivo_ppm(g: Guion, idioma: str) -> float:
    """Palabras por minuto para que el vídeo completo dure unos 9 min (prueba: el ritmo de siempre)."""
    base = OBJETIVO_PPM * 1.06
    if g.modo == "prueba":
        return base
    frases = g.frases()
    palabras = sum(len(f.limpio(idioma).split()) for f in frases)
    caps = sum(1 for sec in g.secciones if sec.tipo == "capitulo")
    fijo = len(frases) * PAUSA + caps * PAUSA_CAPITULO + PAUSA_CASO + 5.5  # pausas, títulos y cierre
    voz = max(60.0, DUR_OBJETIVO - fijo)
    return max(150.0, min(195.0, palabras / voz * 60))


def renderizar(g: Guion, carpeta: Path, cache: Path, procesos: int | None = None) -> dict:
    """Hace los vídeos en los dos idiomas. Devuelve {idioma: {mp4, miniatura, linea, musica, avisos}}."""
    carpeta.mkdir(parents=True, exist_ok=True)
    avisos: list[str] = []
    hasta = DUR_PRUEBA if g.modo == "prueba" else None
    lineas = {}
    for i in ("en", "es"):
        nars = {papel: Narrador(i, cache, papel) for papel in ("narrador", "sarah")}
        ppm_obj = objetivo_ppm(g, i)
        for papel, nar in nars.items():
            textos = [f.limpio(i) for f in g.frases() if f.voz[i] == papel] or [f.limpio(i) for f in g.frases()]
            ppm, vel = nar.calibrar(textos, ppm_obj)
            print(f"🎙 {i}/{papel}: {nar.voz}, {ppm:.0f} ppm natural → {vel} (objetivo {ppm_obj:.0f} ppm)")
        lineas[i] = linea_de_tiempo(g, i, nars, hasta)
        for _ in range(2):  # la velocidad de Edge no es exacta: se corrige con la duración real (8:45-9:15)
            if hasta is not None or abs(lineas[i].duracion - DUR_OBJETIVO) <= 15:
                break
            fijo = lineas[i].duracion - sum(loc.duracion for _, loc, _ in lineas[i].frases)
            factor = (lineas[i].duracion - fijo) / max(60.0, DUR_OBJETIVO - fijo)
            for nar in nars.values():
                actual = 1 + int(nar.velocidad.rstrip("%")) / 100
                nar.velocidad = f"{max(-25, min(35, int(round((actual * factor - 1) * 100)))):+d}%"
            print(f"🎙 {i}: {lineas[i].duracion:.0f} s → reajuste a {nars['narrador'].velocidad}")
            lineas[i] = linea_de_tiempo(g, i, nars, hasta)
        print(f"⏱ {i}: {lineas[i].duracion:.1f} s")
        for nar in nars.values():
            avisos += [f"[{i}] {a}" for a in dict.fromkeys(nar.avisos)]
    # Clips: los mismos en los dos idiomas (hacen falta tantos como el idioma que más trozos tenga).
    buscador = Buscador(cache, avisos)
    todas = g.frases()
    por_frase: dict[int, list] = {}
    for fi, f in enumerate(todas):
        necesarios = max([len([t for t in ln.trozos if t.frase == fi]) for ln in lineas.values()] + [0])
        if necesarios:
            dur = [max(t.dur for ln in lineas.values() for t in ln.trozos if t.frase == fi)] * necesarios
            por_frase[fi] = buscador.elegir(f, dur)
    registro = []
    discoteca = Discoteca(cache)
    musicas: dict = {}
    salida = {}
    nombre_fuente, archivo_fuente = fuente()
    for idioma, ln in lineas.items():
        trabajos = []
        tmp = Path(tempfile.mkdtemp(prefix=f"doc_{idioma}_"))
        for k, tr in enumerate(ln.trozos):
            fi = tr.frase if tr.frase in por_frase else max(por_frase)
            clips = por_frase[fi]
            c, ruta = clips[min(tr.n, len(clips) - 1)]
            info = sondear(ruta)
            libre = max(0.0, info["duracion"] - tr.dur - 0.6)
            desde = 0.3 + libre * 0.35
            n = int(round((tr.inicio + tr.dur) * FPS)) - int(round(tr.inicio * FPS))  # suma exacta de fotogramas
            trabajos.append((str(ruta), desde, tr.dur, tmp / f"t{k:04d}.mp4", hash((g.id, k)) & 0xFFFF, n))
            registro.append({"idioma": idioma, "inicio": round(tr.inicio, 2), "dur": round(tr.dur, 2),
                             "frase": todas[fi].texto["en"][:70], "clip": c.pagina or c.clave})
        with mp.get_context("fork").Pool(procesos or os.cpu_count() or 2) as pool:
            hechos = pool.map(_render_trozo, trabajos, chunksize=1)
        lista = tmp / "lista.txt"
        lista.write_text("".join(f"file '{h}'\n" for h in hechos))
        base = tmp / "base.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy",
                        str(base)], check=True)
        pista, titulos_musica = mezcla(ln, discoteca, musicas)
        wav = tmp / "audio.wav"
        from ..audio import guardar_wav

        guardar_wav(wav, pista)
        ass = tmp / "subs.ass"
        ass.write_text(subtitulos(ln, nombre_fuente, fuente_fina()), encoding="utf-8")
        mp4 = carpeta / f"{g.nombre(idioma)}.mp4"
        kbps = int(min(6000, 86e6 * 8 / ln.duracion / 1000 - 200))  # siempre por debajo de ~90 MB
        filtros = (f"tpad=stop_mode=clone:stop_duration=1,trim=duration={ln.duracion:.3f},setpts=PTS-STARTPTS,vignette=angle=PI/9:mode=forward,"
                   f"noise=alls=5:allf=t,drawbox=x=0:y=0:w=iw:h={FRANJA}:color=black:t=fill,"
                   f"drawbox=x=0:y=ih-{FRANJA}:w=iw:h={FRANJA}:color=black:t=fill,"
                   f"ass={ass}:fontsdir={Path(archivo_fuente).parent},format=yuv420p")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(base), "-i", str(wav), "-map", "0:v:0", "-map", "1:a:0",
                        "-vf", filtros, "-c:v", "libx264", "-profile:v", "high", "-preset", "medium", "-tune", "film",
                        "-crf", "20", "-maxrate", f"{kbps}k", "-bufsize", f"{2 * kbps}k", "-pix_fmt", "yuv420p",
                        "-r", str(FPS), "-fps_mode", "cfr", "-color_primaries", "bt709", "-color_trc", "bt709",
                        "-colorspace", "bt709", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                        "-t", f"{ln.duracion:.3f}", "-movflags", "+faststart", str(mp4)], check=True)
        mini = carpeta / f"{g.nombre(idioma)}_miniatura.png"
        miniatura(base, mini, g.cab(idioma, "miniatura", g.cab(idioma, "titulo")), archivo_fuente)  # del plano limpio, sin subtítulos
        salida[idioma] = {"mp4": mp4, "miniatura": mini, "linea": ln, "musica": titulos_musica}
        print(f"✔ {mp4.name}: {ln.duracion:.1f} s, {mp4.stat().st_size / 1e6:.1f} MB")
    (carpeta / f"{g.id}_clips.json").write_text(json.dumps(registro, ensure_ascii=False, indent=1), encoding="utf-8")
    for d in salida.values():
        d["avisos"] = avisos
    return salida


def miniatura(mp4: Path, destino: Path, texto: str, archivo_fuente: str, seg: float = 4.0):
    """1280x720: un fotograma real del gancho y el texto grande, en dos líneas."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{seg}", "-i", str(mp4), "-frames:v", "1", "-vf",
                        "scale=1280:720", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True)
    img = Image.fromarray(np.frombuffer(r.stdout, np.uint8).reshape(720, 1280, 3)).convert("RGBA")
    capa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    d.rectangle((0, 0, 1280, 720), fill=(0, 0, 0, 70))
    palabras = texto.upper().split()
    mitad = max(1, len(palabras) // 2)
    lineas = [" ".join(palabras[:mitad]), " ".join(palabras[mitad:])] if len(palabras) > 2 else [texto.upper()]
    tam = 120
    f = ImageFont.truetype(archivo_fuente, tam)
    while max(d.textlength(x, font=f) for x in lineas) > 1180 and tam > 50:
        tam -= 4
        f = ImageFont.truetype(archivo_fuente, tam)
    y = 360 - len(lineas) * tam * 0.58
    colores = [(255, 255, 255), (255, 214, 0)]
    for k, x in enumerate(lineas):
        w = d.textlength(x, font=f)
        d.text(((1280 - w) / 2, y), x, font=f, fill=colores[k % 2] + (255,), stroke_width=7, stroke_fill=(0, 0, 0, 255))
        y += tam * 1.12
    Image.alpha_composite(img, capa).convert("RGB").save(destino)
