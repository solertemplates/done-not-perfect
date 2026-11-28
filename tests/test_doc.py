"""Vídeos largos estilo documental: guion, línea de tiempo, color, subtítulos, textos y un montaje corto
de principio a fin con piezas de prueba (sin red: voz, clips y música falsos)."""
import subprocess
from pathlib import Path

import numpy as np
import pytest

from dnp.config import ErrorConfig
from dnp.doc import clips as cl
from dnp.doc import guion as gu
from dnp.doc import montaje as mo
from dnp.doc import musica as mu
from dnp.doc import textos as tx
from dnp.doc import voz as vz

RAIZ = Path(__file__).resolve().parent.parent
EJEMPLO = RAIZ / "episodios_largos" / "01_caso_mismo_sueldo_guion_en.txt"


# --------------------------------------------------------------------- guion
def test_lee_el_caso_en_dos_archivos():
    g = gu.cargar(EJEMPLO)
    assert g.id == "caso01_mismo_sueldo" and g.modo == "completo"
    assert gu.cargar(EJEMPLO.with_name("01_caso_mismo_sueldo_guion_es.txt")).id == g.id  # vale cualquiera de los dos
    assert g.nombre("en") == "caso01_mismo_sueldo_en"
    assert g.cab("en", "expediente") == "CASE 01: SAME SALARY" and g.cab("es", "expediente") == "CASO 01: MISMO SUELDO"
    assert g.cab("es", "producto") == "budget planner"  # lo que no se traduce se toma del inglés
    assert [s.tipo for s in g.secciones] == ["gancho"] + ["capitulo"] * 5 + ["final"]
    f = g.frases()[2]
    assert f.limpio("en") == "Ten years later, one of them is free…" and f.limpio("es") == "Diez años después, una es libre…"
    assert ("free…", "verde") in f.palabras("en")
    assert f.quien == "sarah"
    assert any(f.voz["en"] == "sarah" for f in g.frases())  # voz femenina para Sarah y momentos clave
    mug = next(f for f in g.frases() if "red mug" in f.limpio("en"))
    assert mug.objeto[0] == "red mug"
    assert sum(f.grande for f in g.frases()) >= 4  # minigancho cada ~2 min
    assert sum("consistency and discipline" in f.limpio("en") for f in g.frases()) >= 2  # mensaje central


def test_todos_los_casos_son_validos_y_distintos():
    casos = sorted((RAIZ / "episodios_largos").glob("*_guion_en.txt"))
    assert len(casos) >= 3
    gs = [gu.cargar(c) for c in casos]
    assert len({g.id for g in gs}) == len(gs) and len({g.cab("en", "expediente") for g in gs}) == len(gs)
    for g in gs:
        assert g.cab("en", "siguiente") and g.cab("es", "siguiente")  # adelanto del próximo caso


def test_errores_del_guion():
    en = "id: caso09\n\n== GANCHO\n\ntexto: Hi.\nclip: city\nquien: bob\nlugr: casa\n\ntexto: Two.\nclip: city"
    es = "titulo: Hola\n\n== GANCHO\n\ntexto: Hola."
    with pytest.raises(ErrorConfig) as e:
        gu.leer(en, es)
    s = str(e.value)
    assert "'quien' debe ser" in s and "¿Querías decir 'lugar'?" in s and "frase a frase" in s


def test_el_gancho_dura_unos_15_segundos():
    g = gu.cargar(EJEMPLO)
    for idioma in ("en", "es"):
        palabras = sum(len(f.limpio(idioma).split()) for f in g.secciones[0].frases)
        assert 25 <= palabras <= 45, palabras  # a ~165 ppm, entre 9 y 16 s de voz


def test_ritmo_para_unos_9_minutos():
    g = gu.cargar(EJEMPLO)
    for idioma in ("en", "es"):
        assert 150 <= mo.objetivo_ppm(g, idioma) <= 175


# --------------------------------------------------------------------- voz
def test_repartir_tiempos():
    t = vz.repartir("Same salary. Same city.", 2.0)
    assert len(t) == 4 and t[0][1] == 0 and t[-1][2] == pytest.approx(2.0)
    assert all(a[2] <= b[1] + 1e-9 for a, b in zip(t, t[1:]))


def test_voces_por_papel():
    assert vz.VOCES["en"]["sarah"] == ["en-US-AvaNeural"] and vz.VOCES["es"]["sarah"] == ["es-MX-DaliaNeural"]
    assert set(vz.VOCES["es"]["narrador"]) == {"es-US-AlonsoNeural", "es-MX-JorgeNeural"}


def test_calibrar_elige_la_voz_mas_natural(tmp_path, monkeypatch):
    nar = vz.Narrador("es", tmp_path)
    ppm = {"es-US-AlonsoNeural": 150.0, "es-MX-JorgeNeural": 172.0}
    monkeypatch.setattr(nar, "_ppm_natural", lambda muestra: ppm[nar.voz])
    _, vel = nar.calibrar(["Hola."], 175.0)
    assert nar.voz == "es-MX-JorgeNeural" and vel == "+2%"


# --------------------------------------------------------------------- clips
def _cand(tags, dur=15.0, ancho=1920, alto=1080):
    return cl.Candidato("pixabay", 1, "u", ancho, alto, dur, set(tags), 1000)


def test_puntuacion_de_clips():
    b = cl.Buscador.__new__(cl.Buscador)
    assert b.puntuar(_cand({"hands", "writing", "notebook"}), "woman hands writing notebook", "sarah", 5) > 0
    assert b.puntuar(_cand({"animation", "notebook"}), "notebook", "nadie", 5) is None  # aspecto barato
    assert b.puntuar(_cand({"slow motion", "coins"}), "coins", "nadie", 5) is None  # cámara lenta
    assert b.puntuar(_cand({"portrait", "woman"}), "woman", "sarah", 5) is None  # cara de cerca
    assert b.puntuar(_cand({"man", "shopping"}), "shopping", "sarah", 5) is None  # no es Sarah
    assert b.puntuar(_cand({"coins"}, ancho=1280, alto=720), "coins", "nadie", 5) is None  # poca calidad
    assert b.puntuar(_cand({"coins"}, dur=3), "coins", "nadie", 5) is None  # demasiado corto
    assert b.puntuar(_cand({"beach", "dog"}), "hands signing contract", "nadie", 5) is None  # sin relación
    # Si la voz nombra un objeto, tiene que verse ese objeto (nunca otro).
    assert b.puntuar(_cand({"red", "mug", "coins"}), "red mug coins", "nadie", 5, ["red mug", "mug"]) is not None
    assert b.puntuar(_cand({"coffee", "cup", "table"}), "coffee cup", "nadie", 5, ["red mug", "mug"]) is None


# --------------------------------------------------------------------- color
def test_etalonaje_normaliza_clips_distintos():
    rng = np.random.default_rng(1)
    oscuro = (rng.random((90, 160, 3)) * 60).astype(np.uint8)
    azulado = np.clip(rng.random((90, 160, 3)) * 200 + [0, 20, 60], 0, 255).astype(np.uint8)
    medias = []
    for m in (oscuro, azulado):
        out = mo.etalonar(m, mo.tablas_clip(m)).astype(float)
        luma = out @ [0.2126, 0.7152, 0.0722]
        medias.append(luma.mean())
    assert abs(medias[0] - medias[1]) < 25  # brillo parecido aunque los clips sean muy distintos
    # La dominante azul se reduce mucho, y un gris neutro sale cálido (la LUT de cine).
    antes = azulado[..., 2].mean() - azulado[..., 0].mean()
    out = mo.etalonar(azulado, mo.tablas_clip(azulado)).astype(float)
    assert out[..., 2].mean() - out[..., 0].mean() < antes * 0.5
    gris = np.full((40, 40, 3), 128, np.uint8) + rng.integers(0, 60, (40, 40, 1)).astype(np.uint8)
    out = mo.etalonar(gris, mo.tablas_clip(gris)).astype(float)
    assert out[..., 0].mean() > out[..., 2].mean() + 3


# --------------------------------------------------------------------- subtítulos
class _NarradorFalso:
    def __init__(self, idioma):
        self.idioma = idioma

    def decir(self, texto):
        n = len(texto.split())
        dur = n / 165 * 60
        audio = (0.3 * np.sin(np.arange(int(dur * vz.SR)) * 2 * np.pi * 180 / vz.SR)).astype(np.float32)
        return vz.Locucion(audio, vz.repartir(texto, dur), "falso")


def _caso(modo="prueba"):
    g = gu.cargar(EJEMPLO)
    g.modo = modo
    return g


def test_linea_de_tiempo_y_subtitulos():
    g = _caso()
    nars = {"narrador": _NarradorFalso("en"), "sarah": _NarradorFalso("en")}
    ln = mo.linea_de_tiempo(g, "en", nars, 60.0)
    assert ln.duracion == 60.0
    assert sum(t.dur for t in ln.trozos) == pytest.approx(60.0, abs=0.05)
    duraciones = [t.dur for t in ln.trozos]
    assert all(1.5 <= d <= 5.0 for d in duraciones)  # un clip nuevo cada pocos segundos, nunca más de 5
    assert 2.5 <= np.mean(duraciones) <= 4.5
    caso = ln.tarjetas[0]
    assert caso[2] == "caso" and caso[3] == ["CASE 01: SAME SALARY", "Portland, Oregon · 2014"]
    assert 11 < caso[0] < 18  # el gancho dura unos 15 s
    assert ln.titulos[0][1] == "CHAPTER 1: THE PROMISE" and ln.titulos[0][2] == "YEAR 2014"
    assert ln.evidencias and ln.evidencias[0][2].startswith("EVIDENCE #01 · PAYSLIP")
    ass = mo.subtitulos(ln, "DejaVu Sans", "DejaVu Sans")
    assert "\\fscx112" in ass  # la palabra que suena crece
    assert mo.COLORES_ASS["verde"] in ass and mo.COLORES_ASS["rojo"] in ass and mo.COLORES_ASS["amarillo"] in ass
    es = mo.linea_de_tiempo(g, "es", _NarradorFalso("es"), 60.0)
    t = mo.subtitulos(es, "DejaVu Sans")
    assert "CAPÍTULO 1: LA PROMESA" in t and "CASO 01: MISMO SUELDO" in t and "EVIDENCIA #01" in t


def test_musica_nunca_pasa_de_20_s_y_cambia_en_una_escena():
    g = _caso("completo")
    ln = mo.linea_de_tiempo(g, "en", _NarradorFalso("en"), None)
    assert 400 < ln.duracion < 700
    cues = [t for t, _ in ln.secciones]
    limites = cues + [ln.duracion]
    assert all(b - a <= mo.MAX_MUSICA + 1e-6 for a, b in zip(limites, limites[1:]))
    inicios = {round(t.inicio, 3) for t in ln.trozos if t.n == 0} | {0.0}
    assert all(round(c, 3) in inicios for c in cues), "cada cambio de música coincide con una escena nueva"
    assert ln.tarjetas[-1][2] == "siguiente" and "CASE 02" in ln.tarjetas[-1][3][1]


def test_transiciones_lentas_y_nunca_silencio():
    t = np.arange(0, 30, 0.01)
    env = mo.envolvente_musica(t, 10.0, 20.0, False, False)
    assert env[t < 9.0].max() < 0.2  # antes de entrar, casi nada
    assert env[(t > 13) & (t < 17)].min() == pytest.approx(1.0)
    assert np.all(np.diff(env[(t > 9.5) & (t < 13)]) >= -1e-9)  # entra suave


# --------------------------------------------------------------------- textos
def test_textos_en_los_dos_idiomas():
    g = gu.cargar(EJEMPLO)
    for idioma, titulo in (("en", "Same Salary, Different Life"), ("es", "Mismo sueldo, otra vida")):
        ln = mo.linea_de_tiempo(g, idioma, _NarradorFalso(idioma), None)
        t = tx.generar(g, idioma, ln, ["Heartwarming"])
        assert t.startswith(titulo)
        assert "0:00" in t and "As an Amazon Associate I earn from qualifying purchases." in t
        assert "PRIMER COMENTARIO" in t and "https://www.amazon.com/s?k=budget+planner&tag=styleesencial-20" in t
        assert "Kevin MacLeod (incompetech.com)" in t
        assert t.rstrip().endswith("purposes.)") or "Story dramatized for educational purposes." in t
        assert ("CASE 02" in t) if idioma == "en" else ("CASO 02" in t and "Un rato con Rene" in t)
        for palabra in ("guarantee", "get rich", "make money fast", "millionaire", "garantiza", "hazte rico"):
            assert palabra not in t.lower()


def test_musica_se_repite_con_fundido():
    x = np.ones((mu.SR * 2, 2), np.float32) * 0.1
    y = mu.ajustar(x, 5.0, fundido=0.5)
    assert y.shape == (mu.SR * 5, 2) and np.isfinite(y).all()


# --------------------------------------------------------------------- de principio a fin (corto)
def test_montaje_corto_de_principio_a_fin(tmp_path, monkeypatch):
    """Monta 8 s en los dos idiomas con piezas falsas y pasa las comprobaciones de siempre."""
    clips = []
    for k, color in enumerate(("red", "blue", "green", "orange", "purple", "yellow")):
        p = tmp_path / f"c{k}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                        "testsrc2=size=1920x1080:rate=30:duration=8,hue=s=0.6", "-vf",
                        f"drawbox=x=0:y=0:w=300:h=300:color={color}:t=fill", "-c:v", "libx264", "-preset",
                        "ultrafast", str(p)], check=True)
        clips.append(p)
    musica = tmp_path / "m.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=20",
                    "-ac", "2", str(musica)], check=True)

    class BuscadorFalso:
        def __init__(self, cache, avisos=None):
            self.i = 0

        def elegir(self, frase, segundos):
            out = []
            for _ in segundos:
                out.append((cl.Candidato("pixabay", self.i, "", 1920, 1080, 8, set(), 1, f"clip{self.i}"),
                            clips[self.i % len(clips)]))
                self.i += 1
            return out

    class DiscotecaFalsa:
        def __init__(self, cache):
            pass

        def cancion(self, ambiente, evitar=None):
            return mu.leer(musica), "Prueba"

    class NarradorFalso(_NarradorFalso):
        def __init__(self, idioma, cache, papel="narrador"):
            super().__init__(idioma)
            self.velocidad = "+0%"
            self.avisos, self.voz = [], "falsa"

        def calibrar(self, frases, objetivo=None):
            return 165.0, "+0%"

    monkeypatch.setattr(mo, "Buscador", BuscadorFalso)
    monkeypatch.setattr(mo, "Discoteca", DiscotecaFalsa)
    monkeypatch.setattr(mo, "Narrador", NarradorFalso)
    monkeypatch.setattr(mo, "DUR_PRUEBA", 8.0)
    g = _caso()
    res = mo.renderizar(g, tmp_path / "out", tmp_path / "cache", procesos=2)
    from dnp.doc.__main__ import comprobar

    for idioma in ("en", "es"):
        r = res[idioma]
        assert r["mp4"].name == f"caso01_mismo_sueldo_prueba_{idioma}.mp4"
        malos = [c for c in comprobar(r["mp4"], r["miniatura"], 8.0, True) if not c.ok]
        assert not malos, malos
