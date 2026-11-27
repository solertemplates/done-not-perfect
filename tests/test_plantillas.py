"""Guiones cortos (.txt) con plantillas."""
from pathlib import Path

import pytest

from dnp import publicar
from dnp.config import ErrorConfig, validar
from dnp.plantillas import PROPIOS, convertir, ejemplo
from tests.test_publicar import falso_render

TXT = Path("episodios/07_kioscos.txt")


@pytest.mark.parametrize("plantilla", list(PROPIOS))
def test_cada_plantilla_da_un_episodio_valido(plantilla):
    d = convertir(ejemplo(plantilla), Path(f"episodios/09_{plantilla}.txt"))
    validar(d)
    assert d["episodio"] == 9 and d["id"] == f"ep09_{plantilla}"


def test_ejemplo_del_usuario_con_comillas_curvas_y_flecha():
    texto = "plantilla: kioscos\nbarato: “$1”\ncaro: $3 → $5\ngancho: Same lemonade.\ncierre: Smart > Cheap\nfondo: azul_noche"
    d = convertir(texto, TXT)
    validar(d)
    objetos = {o["id"]: o for o in d["guion"]["objetos"]}
    assert objetos["precio_b"]["precio"] == "$1" and objetos["precio_c"]["precio"] == "$3"
    hacedor = next(p for p in d["guion"]["personajes"] if p["tipo"] == "hacedor")
    assert [a["precio"] for a in hacedor["acciones"] if a["accion"] == "cambiar_precio"] == ["$5"]
    assert d["textos"] == {**d["textos"], "gancho": "Same lemonade.", "cierre": "Smart > Cheap"}
    assert d["fondo"] == "azul_noche" and d["id"] == "ep07_kioscos" and d["episodio"] == 7


def test_caro_sin_flecha_no_cambia_precio():
    d = convertir("plantilla: kioscos\ncaro: $4\nclientes: 3", TXT)
    validar(d)
    hacedor = next(p for p in d["guion"]["personajes"] if p["tipo"] == "hacedor")
    assert all(a["accion"] != "cambiar_precio" for a in hacedor["acciones"])


def test_roca_golpes():
    d = convertir("plantilla: roca\ngolpes: 30\ngancho: 30 hits.", Path("episodios/08_roca.txt"))
    validar(d)
    rocas = [o for z in ("arriba", "abajo") for o in d["guion"][z]["objetos"] if o["tipo"] == "roca"]
    assert {r["golpes_para_partir"] for r in rocas} == {31}


def test_construir_escalera():
    d = convertir("Plantilla: Construir\nobjeto: Escalera", Path("episodios/10_escalera.txt"))
    validar(d)
    assert "escalera" in str(d["guion"])


def test_campo_mal_escrito_sugiere():
    with pytest.raises(ErrorConfig) as e:
        convertir("plantilla: kioscos\nbarto: $1", TXT)
    assert "¿Querías decir 'barato'?" in str(e.value)


def test_plantilla_mal_escrita_y_falta_plantilla():
    with pytest.raises(ErrorConfig) as e:
        convertir("plantilla: kiosco\n", TXT)
    assert "¿Querías decir \"kioscos\"?" in str(e.value)
    with pytest.raises(ErrorConfig) as e:
        convertir("gancho: hola", TXT)
    assert "Falta la línea 'plantilla:'" in str(e.value)


def test_texto_largo_lo_detecta_el_validador():
    with pytest.raises(ErrorConfig) as e:
        validar(convertir("plantilla: martillos\ncierre: " + "x" * 30, TXT))
    assert "textos.cierre" in str(e.value)


def test_publicar_un_txt(tmp_path):
    txt = tmp_path / "07_kioscos.txt"
    txt.write_text(ejemplo("kioscos"), encoding="utf-8")
    destino = tmp_path / "videos"
    assert publicar.procesar([txt], destino, tmp_path / "salida", render=falso_render) == 0
    assert (destino / "ep07_kioscos.mp4").exists()
    assert (tmp_path / "salida" / "07_kioscos" / "07_kioscos.json").exists()


def test_publicar_un_txt_con_errores(tmp_path):
    txt = tmp_path / "07_kioscos.txt"
    txt.write_text("plantilla: kioscos\nclientes: muchos", encoding="utf-8")
    destino = tmp_path / "videos"
    assert publicar.procesar([txt], destino, tmp_path / "salida", render=falso_render) == 1
    assert "'clientes' debe ser un número" in (destino / "ERRORES.txt").read_text("utf-8")
