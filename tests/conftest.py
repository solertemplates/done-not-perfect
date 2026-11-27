import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
EP1 = RAIZ / "tests" / "datos" / "episodios" / "ep01_la_silla.json"
EP2 = RAIZ / "tests" / "datos" / "episodios" / "ep02_la_escalera.json"
EP3 = RAIZ / "tests" / "datos" / "episodios" / "ep03_los_dos_martillos.json"
EP4 = RAIZ / "tests" / "datos" / "episodios" / "04_roca.json"
EP9 = RAIZ / "tests" / "datos" / "episodios" / "09_paneles.json"  # plantilla paneles (franjas) con lección
EPISODIOS = [EP1, EP2, EP3, EP4, EP9]


def _crear(ruta):
    from dnp.config import cargar
    from dnp.render import crear_escena

    return crear_escena(cargar(ruta))


def _leer(ruta):
    return json.loads(ruta.read_text(encoding="utf-8"))


@pytest.fixture
def datos():
    return _leer(EP1)


@pytest.fixture
def datos_roca():
    return _leer(EP4)


@pytest.fixture
def datos_martillos():
    return _leer(EP3)


@pytest.fixture(scope="session")
def escena():
    return _crear(EP1)


@pytest.fixture(scope="session")
def escalera():
    return _crear(EP2)


@pytest.fixture(scope="session")
def martillos():
    return _crear(EP3)


@pytest.fixture(scope="session")
def roca():
    return _crear(EP4)


@pytest.fixture(scope="session", params=EPISODIOS, ids=lambda p: p.stem)
def cada_escena(request):
    return _crear(request.param)
