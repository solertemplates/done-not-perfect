"""Textos para publicar (videos/<id>_textos.txt) y variedad entre episodios."""
import re
from pathlib import Path

import pytest

from dnp import publicar, textos, variedad
from dnp.config import cargar
from dnp.plantillas import convertir, ejemplo
from tests.test_publicar import falso_render

EPISODIOS = sorted(Path("tests/datos/episodios").glob("*.json")) + sorted(Path("dnp/plantillas").glob("*.json"))
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


@pytest.mark.parametrize("ruta", EPISODIOS, ids=lambda p: p.stem)
def test_formato_de_los_textos(ruta):
    t = textos.generar(cargar(ruta).datos)
    fb, yt = t.split("\nYOUTUBE\n")
    assert fb.startswith("FACEBOOK\n")
    lineas_fb = fb.strip().splitlines()[1:]
    post = "\n".join(lineas_fb[:lineas_fb.index(next(x for x in lineas_fb if x.startswith("#")))])
    assert 2 <= len(EMOJI.findall(post)) <= 3  # el texto del post (sin el bloque de Amazon)
    tags = [x for x in lineas_fb if x.startswith("#")]
    assert len(tags) == 1 and len(re.findall(r"#\w+", tags[0])) == 5
    titulo = re.search(r"^Title: (.*)$", yt, re.M).group(1)
    assert len(titulo) <= 60 and "#shorts" in titulo
    desc = yt.split("Description:\n")[1].split("\nHashtags:")[0]
    assert len(desc.strip().splitlines()) == 2 + 3  # 2 líneas y las 3 de Amazon
    hashtags = re.search(r"^Hashtags: (.*)$", yt, re.M).group(1)
    assert len(hashtags.split()) == 5 and len(set(hashtags.split())) == 5
    # Amazon: 3 líneas fijas al final de FACEBOOK y de la descripción de YOUTUBE, y el primer comentario
    yt, comentario = yt.split("\nPRIMER COMENTARIO\n")
    desc_yt = yt.split("Description:\n")[1].split("Hashtags:")[0].strip().splitlines()
    for lineas in (fb.strip().splitlines(), desc_yt):
        assert lineas[-1] == "As an Amazon Associate I earn from qualifying purchases."
        assert re.fullmatch(r"\S+ Get this .+ and .+ — link in the first comment 👇", lineas[-2])
        assert "amazon.com" not in lineas[-3]  # la frase puente no lleva enlace
    c = comentario.strip().splitlines()
    assert len(c) == 2 and c[0].endswith("👇")
    assert re.fullmatch(r"https://www\.amazon\.com/s\?k=[\w+]+&tag=styleesencial-20", c[1])

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


@pytest.mark.parametrize("plantilla,productos", [
    ("roca", {"sledgehammer", "Atomic Habits"}), ("paneles", {"sledgehammer", "Atomic Habits"}),
    ("construir", {"step ladder"}), ("kioscos", {"lemonade dispenser", "lemonade stand"}), ("martillos", {"home tool kit"}),
])
def test_producto_que_se_ve_en_el_video(plantilla, productos):
    d = convertir(ejemplo(plantilla), Path(f"/no_existe/09_{plantilla}.txt"))
    assert textos.amazon_partes(d)["producto"] in productos


def test_silla_lleva_desk_chair_y_lampara_como_alternativa():
    d = convertir("plantilla: construir\nobjeto: silla", Path("/no_existe/09_silla.txt"))
    assert textos.candidatos(d) == ["desk chair", "desk lamp"]
    assert textos.amazon_partes(d)["producto"] == "desk chair"
    assert textos.amazon_partes(d, anterior="desk chair")["producto"] == "desk lamp"


def test_roca_alterna_mazo_y_libro():
    p = [textos.amazon_partes(convertir(ejemplo("roca"), Path(f"/no_existe/{n:02d}_roca.txt")))["producto"]
         for n in (8, 9)]
    assert set(p) == {"sledgehammer", "Atomic Habits"}


def test_portatil_si_sale_en_el_video():
    d = convertir(ejemplo("martillos"), Path("/no_existe/09_m.txt"))
    d["guion"]["objetos"].append({"tipo": "laptop"})
    assert "laptop" in textos.candidatos(d)


def test_al_menos_10_variantes_de_cada_parte():
    assert len(textos.PUENTES) >= 10 and len(textos.PUENTES_LIBRO) >= 10
    assert all(len(v) >= 10 for v in textos.ACCIONES.values())
    assert len(textos.EMOJIS_AMAZON) >= 10 and len(textos.COMENTARIOS) >= 10


def test_sin_promesas_de_exito_ni_dinero():
    todo = " ".join(textos.PUENTES + textos.PUENTES_LIBRO + textos.COMENTARIOS
                    + [x for v in textos.ACCIONES.values() for x in v]
                    + [x for v in textos.LECCIONES.values() for x in v]).lower()
    for palabra in ("guarantee", "rich", "earn money", "make money", "success", "profit", "income", "millionaire"):
        assert palabra not in todo


def test_episodios_seguidos_nunca_repiten_ninguna_parte():
    def partes(n):
        d = convertir(ejemplo("kioscos"), Path(f"/no_existe/{n:02d}_k.txt"))
        a = textos.amazon_partes(d)
        l1, l2, _ = a["descripcion"].splitlines()
        return l1.split(". ")[0], l2.split(" ")[0], l2.split(" and ", 1)[1], a["comentario"].splitlines()[0]

    todas = [partes(n) for n in range(1, 31)]
    for a, b in zip(todas, todas[1:]):
        assert all(x != y for x, y in zip(a, b)), (a, b)
    assert len(set(todas)) == len(todas)  # nunca dos publicaciones iguales


def test_nunca_el_mismo_producto_dos_episodios_seguidos(tmp_path):
    guiones = ["roca", "roca", "construir\nobjeto: silla", "construir\nobjeto: silla", "kioscos", "kioscos",
               "kioscos", "martillos", "martillos", "roca", "construir\nobjeto: escalera",
               "construir\nobjeto: escalera", "paneles\npaneles: A, B, C", "paneles\npaneles: A, B, C"]
    productos = []
    for n, g in enumerate(guiones, 1):
        f = tmp_path / f"{n:02d}_ep.txt"
        f.write_text(f"plantilla: {g}\n", encoding="utf-8")
    for n in range(1, len(guiones) + 1):
        f = tmp_path / f"{n:02d}_ep.txt"
        a = textos.amazon_partes(convertir(f.read_text(), f), anterior=textos.producto_anterior(f))
        productos.append(a["producto"])
    assert all(a != b for a, b in zip(productos, productos[1:])), productos


def test_sin_config_de_amazon_no_hay_bloque(monkeypatch, tmp_path):
    monkeypatch.setattr(textos, "AMAZON", tmp_path / "no.txt")
    t = textos.generar(convertir(ejemplo("roca"), Path("/no_existe/09_roca.txt")))
    assert "amazon" not in t.lower()


def test_config_amazon():
    conf = textos.amazon()
    assert conf["tienda"] == "amazon.com" and conf["id"] == "styleesencial-20"
