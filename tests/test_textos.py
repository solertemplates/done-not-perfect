"""Textos para publicar (videos/<id>_textos.txt) y variedad entre episodios."""
import re
from pathlib import Path

import pytest

from dnp import publicar, textos, variedad
from dnp.config import cargar
from dnp.plantillas import convertir, ejemplo
from tests.test_publicar import falso_render

EPISODIOS = sorted(Path("episodios").glob("*.json"))
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


@pytest.mark.parametrize("ruta", EPISODIOS, ids=lambda p: p.stem)
def test_formato_de_los_textos(ruta):
    t = textos.generar(cargar(ruta).datos)
    fb, yt = t.split("\nYOUTUBE\n")
    assert fb.startswith("FACEBOOK\n")
    lineas_fb = fb.strip().splitlines()[1:]
    assert 2 <= len(EMOJI.findall(fb)) <= 3
    assert len(re.findall(r"#\w+", lineas_fb[-1])) == 5
    titulo = re.search(r"^Title: (.*)$", yt, re.M).group(1)
    assert len(titulo) <= 60 and "#shorts" in titulo
    desc = yt.split("Description:\n")[1].split("\nHashtags:")[0]
    assert len(desc.strip().splitlines()) == 2
    hashtags = re.search(r"^Hashtags: (.*)$", yt, re.M).group(1)
    assert len(hashtags.split()) == 5 and len(set(hashtags.split())) == 5


def test_tema_segun_el_episodio():
    assert textos.tema(convertir(ejemplo("roca"), Path("09_roca.txt"))) == "constancia"
    assert textos.tema(convertir(ejemplo("kioscos"), Path("09_k.txt"))) == "negocio"
    assert textos.tema(convertir(ejemplo("martillos"), Path("09_m.txt"))) == "perfeccionismo"


def test_titulo_largo_se_recorta():
    d = convertir(ejemplo("kioscos"), Path("09_k.txt"))
    d["textos"]["gancho"] = "x" * 40
    d["textos"]["cierre"] = "y" * 24
    titulo = re.search(r"^Title: (.*)$", textos.generar(d), re.M).group(1)
    assert len(titulo) <= 60 and titulo.endswith("#shorts")


def test_publicar_deja_el_archivo_de_textos(tmp_path):
    txt = tmp_path / "07_kioscos.txt"
    txt.write_text(ejemplo("kioscos"), encoding="utf-8")
    destino = tmp_path / "videos"
    publicar.procesar([txt], destino, tmp_path / "salida", render=falso_render)
    t = (destino / "ep07_kioscos_textos.txt").read_text(encoding="utf-8")
    assert "FACEBOOK" in t and "YOUTUBE" in t


def test_fondo_automatico_distinto_de_los_recientes(tmp_path):
    usados = []
    for n in range(1, 16):
        f = tmp_path / f"{n:02d}_kioscos.txt"
        f.write_text("plantilla: kioscos\n", encoding="utf-8")
        usados.append(convertir(f.read_text(), f)["fondo"])
    for i, fondo in enumerate(usados):
        assert fondo not in usados[max(0, i - 6):i]


def test_fondo_puesto_a_mano_se_respeta(tmp_path):
    f = tmp_path / "07_kioscos.txt"
    f.write_text("plantilla: kioscos\nfondo: rosa", encoding="utf-8")
    assert convertir(f.read_text(), f)["fondo"] == "rosa"


def test_variaciones_distintas_por_episodio():
    vs = [variedad.para(f"ep{n:02d}_x") for n in range(1, 13)]
    assert len({(v.semilla, round(v.dx), round(v.dy)) for v in vs}) == 12
    assert variedad.para("ep01_x") == variedad.para("ep01_x")


def test_faltan_videos(tmp_path, monkeypatch):
    (tmp_path / "episodios").mkdir()
    (tmp_path / "videos").mkdir()
    for n in (7, 8):
        (tmp_path / "episodios" / f"{n:02d}_roca.txt").write_text("plantilla: roca\n", encoding="utf-8")
    (tmp_path / "videos" / "ep07_roca.mp4").write_bytes(b"x")
    monkeypatch.setattr(publicar, "RAIZ", tmp_path)
    assert [p.name for p in publicar.sin_video(tmp_path / "videos")] == ["08_roca.txt"]
