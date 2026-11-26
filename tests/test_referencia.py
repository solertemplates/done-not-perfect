"""Los episodios salen siempre igual: cada 15 fotogramas se compara su huella con la de referencia.

Si un cambio visual es intencionado, regenera las referencias con:
    python tests/referencias/regenerar.py
"""
import hashlib
import json
from pathlib import Path

import pytest

from tests.conftest import EPISODIOS, _crear

REFERENCIAS = Path(__file__).parent / "referencias"


@pytest.mark.parametrize("ruta", EPISODIOS, ids=lambda p: p.stem)
def test_episodio_igual_que_la_referencia(ruta):
    ref = json.loads((REFERENCIAS / f"{ruta.stem}.json").read_text())["fotogramas"]
    e = _crear(ruta)
    distintos = [i for i in range(0, len(ref), 15)
                 if hashlib.sha1(e.fotograma(i / e.ep.fps).tobytes()).hexdigest() != ref[i]]
    assert not distintos, f"{ruta.stem}: cambian los fotogramas {distintos}"
