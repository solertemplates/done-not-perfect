"""Etiquetas, marcadores, lección, plantilla paneles (franjas), brillo y publicación sin bloqueos."""
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from dnp import publicar
from dnp.config import ErrorConfig, validar
from dnp.lienzo import BLANCO, FONDOS, ROJO, VERDE
from dnp.plantillas import convertir, ejemplo
from dnp.render import crear_escena
from tests.test_publicar import falso_render

TXT = Path("/no_existe/09_x.txt")


def _ep(texto):
    return crear_escena(validar(convertir(texto, TXT)))


# ------------------------------------------------------------------ etiquetas
def test_etiquetas_por_defecto_done_y_perfect():
    d = convertir(ejemplo("roca"), TXT)
    g = d["guion"]
    assert g["arriba"]["personajes"][0]["etiqueta"]["texto"] == "DONE"
    assert g["abajo"]["personajes"][0]["etiqueta"]["texto"] == "PERFECT"


@pytest.mark.parametrize("plantilla", ["roca", "kioscos", "construir", "martillos"])
def test_etiquetas_propias(plantilla):
    d = convertir(ejemplo(plantilla) + "\netiqueta_arriba: builder\netiqueta_abajo: “Dreamer”", TXT)
    validar(d)
    textos = {p["etiqueta"]["texto"] for z in ([d["guion"]["arriba"], d["guion"]["abajo"]]
                                              if "arriba" in d["guion"] else [d["guion"]]) for p in z["personajes"]}
    assert textos == {"BUILDER", "DREAMER"}


def test_etiqueta_demasiado_larga():
    with pytest.raises(ErrorConfig) as e:
        convertir(ejemplo("roca") + "\netiqueta_arriba: " + "x" * 20, TXT)
    assert "etiqueta_arriba" in str(e.value)


def test_etiqueta_cambia_de_color_al_final():
    from dnp.rotulos import color_etiqueta

    e = {"texto": "DONE", "color_final": "verde", "desde_s": 14.0}
    assert color_etiqueta(e, 13.0) == BLANCO and color_etiqueta(e, 15.0) == VERDE


# ------------------------------------------------------------------ marcadores
def test_marcador_de_la_roca_cuenta_golpes_y_done():
    ep = _ep(ejemplo("roca"))
    m_hacedor, m_perf = ep.marcadores[0][0], ep.marcadores[1][0]
    assert m_hacedor.valor("g", 3.0) == 0
    assert 20 < m_hacedor.valor("g", 8.0) < 80
    assert m_hacedor.valor("d", 13.0) == 0 and m_hacedor.valor("d", 15.0) == 1
    assert m_perf.valor("g", 15.0) == 99 and m_perf.valor("d", 15.0) == 0


@pytest.mark.parametrize("plantilla", ["kioscos", "construir", "martillos"])
def test_marcadores_suben_durante_la_accion(plantilla):
    ep = _ep(ejemplo(plantilla))
    for marcadores in ep.marcadores:
        for m in marcadores:
            primero = [m.valor(n, 3.0) for n in m.fuentes]
            ultimo = [m.valor(n, 15.0) for n in m.fuentes]
            assert all(a <= b for a, b in zip(primero, ultimo))
    total = sum(m.valor(n, 15.0) for ms in ep.marcadores for m in ms for n in m.fuentes)
    assert total > 0


def test_marcador_con_valor_desconocido():
    d = convertir(ejemplo("roca"), TXT)
    d["guion"]["arriba"]["marcadores"] = [{"texto": "HITS {x}", "valores": {}}]
    with pytest.raises(ErrorConfig) as e:
        validar(d)
    assert "usa {x}" in str(e.value)


# -------------------------------------------------------------------- lección
def test_leccion_visible_todo_el_video():
    con = _ep(ejemplo("martillos") + "\nleccion: Done beats perfect, every single day.")
    sin = _ep(ejemplo("martillos"))
    for t in (0.0, 5.0, 12.0):
        a = np.asarray(con.fotograma(t))[:120].astype(int)
        b = np.asarray(sin.fotograma(t))[:120].astype(int)
        assert (np.abs(a - b).sum(-1) > 100).mean() > 0.01


def test_leccion_demasiado_larga():
    with pytest.raises(ErrorConfig) as e:
        validar(convertir(ejemplo("roca") + "\nleccion: " + "x" * 51, TXT))
    assert "textos.leccion" in str(e.value)


# -------------------------------------------------------------------- paneles
@pytest.mark.parametrize("n", [3, 4, 5, 6])
def test_paneles_de_3_a_6(n):
    nombres = ", ".join(f"P{i}" for i in range(n))
    d = convertir(f"plantilla: paneles\npaneles: {nombres}", TXT)
    validar(d)
    assert d["guion"]["formato"] == "franjas" and len(d["guion"]["franjas"]) == n


@pytest.mark.parametrize("nombres", ["A, B", "A, B, C, D, E, F, G"])
def test_paneles_fuera_de_rango(nombres):
    with pytest.raises(ErrorConfig) as e:
        convertir(f"plantilla: paneles\npaneles: {nombres}", TXT)
    assert "de 3 a 6" in str(e.value)


def test_paneles_solo_el_ultimo_rompe_la_roca():
    ep = _ep(ejemplo("paneles"))
    from dnp.rotulos import color_etiqueta

    finales = [color_etiqueta(z[2][0].conf["etiqueta"], 15.0) for z in ep.zonas]
    assert finales[-1] == VERDE and all(c == ROJO for c in finales[:-1])
    rinden = [z[2][0].conf["etiqueta"]["desde_s"] for z in ep.zonas[:-1]]
    assert len(set(rinden)) == len(rinden)  # cada uno se rinde en un momento distinto
    roturas = [sum(1 for e in z[1]["roca"].eventos() if e[1] == "crac") for z in ep.zonas]
    assert roturas == [0] * (len(ep.zonas) - 1) + [1]


# --------------------------------------------------------------------- brillo
def test_brillo_alrededor_de_lo_blanco(escena):
    img = Image.new("RGB", (1080, 1920), FONDOS[escena.ep["fondo"]])
    img.paste(BLANCO, (500, 440, 580, 520))
    out = np.asarray(escena._componer(img)).astype(int)
    sin = np.asarray(escena._componer(Image.new("RGB", (1080, 1920), FONDOS[escena.ep["fondo"]]))).astype(int)
    assert (out[450:510, 510:570] == BLANCO).all()  # lo blanco sigue blanco
    assert out[480, 595].sum() > sin[480, 595].sum() + 15  # resplandor justo al lado
    assert abs(out[480, 900].sum() - sin[480, 900].sum()) < 4  # lejos, nada


# ------------------------------------------------------- publicar sin bloqueos
def test_un_episodio_que_falla_no_bloquea_a_los_demas(tmp_path):
    bueno = tmp_path / "07_roca.txt"
    malo = tmp_path / "08_kioscos.txt"
    bueno.write_text(ejemplo("roca"), encoding="utf-8")
    malo.write_text(ejemplo("kioscos"), encoding="utf-8")

    def render(ruta, salida):
        if "08_kioscos" in str(ruta):
            raise RuntimeError("se rompió")
        return falso_render(ruta, salida)

    destino = tmp_path / "videos"
    assert publicar.procesar([malo, bueno], destino, tmp_path / "s", render=render) == 1
    assert (destino / "ep07_roca.mp4").exists()
    assert "08_kioscos.txt" in (destino / "ERRORES.txt").read_text(encoding="utf-8")


def test_id_repetido_no_bloquea(tmp_path):
    a = tmp_path / "07_roca.txt"
    b = tmp_path / "ep07_roca.json"
    a.write_text(ejemplo("roca"), encoding="utf-8")
    d = convertir(ejemplo("roca"), a)
    b.write_text(json.dumps(d), encoding="utf-8")
    otro = tmp_path / "08_kioscos.txt"
    otro.write_text(ejemplo("kioscos"), encoding="utf-8")
    destino = tmp_path / "videos"
    assert publicar.procesar([a, b, otro], destino, tmp_path / "s", render=falso_render) == 1
    assert (destino / "ep07_roca.mp4").exists() and (destino / "ep08_kioscos.mp4").exists()
    assert "igual que el de" in (destino / "ERRORES.txt").read_text(encoding="utf-8")


def test_numero_repetido_con_otro_nombre_se_publica(tmp_path):
    a = tmp_path / "07_roca.txt"
    b = tmp_path / "07_kioscos.txt"
    a.write_text(ejemplo("roca"), encoding="utf-8")
    b.write_text(ejemplo("kioscos"), encoding="utf-8")
    destino = tmp_path / "videos"
    assert publicar.procesar([a, b], destino, tmp_path / "s", render=falso_render) == 0
    assert (destino / "ep07_roca.mp4").exists() and (destino / "ep07_kioscos.mp4").exists()
