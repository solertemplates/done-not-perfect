import json

from dnp import publicar
from dnp.verificar import Resultado
from tests.conftest import EP1


def falso_render(ruta, salida):
    """Render simulado (rápido) para probar la publicación."""
    from dnp.config import cargar

    salida.mkdir(parents=True, exist_ok=True)
    (salida / "x.mp4").write_bytes(b"mp4")
    (salida / "m.png").write_bytes(b"png")
    return cargar(ruta), salida / "x.mp4", salida / "m.png", [Resultado("Todo", True, "ok")]


def test_json_con_errores_escribe_errores_txt(tmp_path):
    malo = tmp_path / "05_malo.json"
    datos = json.loads(EP1.read_text(encoding="utf-8"))
    del datos["textos"]["cierre"]
    datos["guion"]["arriba"]["personajes"][0]["acciones"][0]["accion"] = "saltarr"
    malo.write_text(json.dumps(datos), encoding="utf-8")
    destino = tmp_path / "videos"
    assert publicar.procesar([malo], destino, tmp_path / "salida", render=falso_render) == 1
    texto = (destino / "ERRORES.txt").read_text(encoding="utf-8")
    assert "Hay que corregir algo" in texto
    assert "05_malo.json" in texto
    assert "Falta el campo obligatorio 'textos.cierre'." in texto
    assert "Cómo arreglarlo" in texto


def test_json_mal_escrito_tambien_avisa(tmp_path):
    malo = tmp_path / "roto.json"
    malo.write_text('{"serie": "Done, not perfect",}', encoding="utf-8")
    destino = tmp_path / "videos"
    assert publicar.procesar([malo], destino, tmp_path / "salida", render=falso_render) == 1
    assert "mal escrito en la línea 1" in (destino / "ERRORES.txt").read_text(encoding="utf-8")


def test_todo_bien_publica_y_avisa_de_borrar_errores(tmp_path):
    destino = tmp_path / "videos"
    assert publicar.procesar([EP1], destino, tmp_path / "salida", render=falso_render) == 0
    assert (destino / "ep01_la_silla.mp4").exists()
    assert (destino / "ep01_la_silla_miniatura.png").exists()
    assert (destino / publicar.SIN_ERRORES).exists()
    assert not (destino / "ERRORES.txt").exists()


def test_comprobacion_fallida_va_a_errores(tmp_path):
    def render_malo(ruta, salida):
        ep, mp4, mini, _ = falso_render(ruta, salida)
        return ep, mp4, mini, [Resultado("Cero fotogramas en negro", False, "black_start:0")]

    destino = tmp_path / "videos"
    assert publicar.procesar([EP1], destino, tmp_path / "s", render=render_malo) == 1
    assert "no pasó la comprobación 'Cero fotogramas en negro'" in (destino / "ERRORES.txt").read_text("utf-8")
