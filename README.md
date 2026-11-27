# Done, not perfect

Serie de vídeos cortos sin voz con dos muñequitos de palo: el **Perfeccionista** (gafas y lápiz en la oreja), que nunca termina, y el **Hacedor**, que lo hace imperfecto pero lo termina.

Todo se genera por código en GitHub Actions: dibujo, animación, música y efectos de sonido.

## Publicar un episodio desde el iPhone

1. En github.com, entra en la carpeta `episodios/` y sube un JSON nuevo (**Add file → Create new file**) o edita uno con el lápiz. Guarda (**Commit changes**).
2. Ya está: el workflow **se lanza solo** y renderiza solo los episodios que has subido o cambiado. No hay que tocar Actions.
3. En unos 3 minutos el vídeo aparece en [`videos/`](videos/), con su miniatura (`<id>_miniatura.png`) y sus textos para publicar (`<id>_textos.txt`). Descarga directa:
   - Ep. 1: https://github.com/solertemplates/done-not-perfect/raw/main/videos/ep01_la_silla.mp4
   - Ep. 2: https://github.com/solertemplates/done-not-perfect/raw/main/videos/ep02_la_escalera.mp4
   - Ep. 3: https://github.com/solertemplates/done-not-perfect/raw/main/videos/ep03_los_dos_martillos.mp4
   - Ep. 4: https://github.com/solertemplates/done-not-perfect/raw/main/videos/ep04_la_roca.mp4
   - Ep. 6: https://github.com/solertemplates/done-not-perfect/raw/main/videos/ep06_limonada.mp4

   Pulsa compartir y elige **Guardar vídeo** para llevarlo a Fotos.
4. **Si el JSON tiene un error**, en vez del vídeo aparece `videos/ERRORES.txt`, que explica en español qué corregir. Al corregirlo y guardar, el vídeo se hace solo y `ERRORES.txt` desaparece.

**Lo más rápido:** un guion corto `.txt` de 5 a 8 líneas con una plantilla (roca, kioscos, construir, martillos o paneles), por ejemplo `episodios/07_kioscos.txt`:

```
plantilla: kioscos
barato: $1
caro: $3 -> $5
gancho: Same lemonade.
cierre: Smart > Cheap
fondo: azul_noche
```

Cómo escribir un episodio (plantillas, escenas, personajes, objetos, acciones, colores y un ejemplo completo): [GUIA_GUIONES.md](GUIA_GUIONES.md).

Cada vídeo pasa siempre las mismas comprobaciones (30 fps, cero negros, bucle y miniatura). Si alguna falla, no se publica y el motivo aparece en `ERRORES.txt`.

> Las comillas curvas `“ ”` que pone el teclado del iPhone se aceptan, tanto en los `.txt` como en los JSON.

## Fondos

Degradado radial: centro de color vivo y bordes oscuros. Los personajes son siempre blancos. Si un `.txt` no dice `fondo:`, se elige uno distinto al de los últimos 6 episodios.

| `"fondo"` | Centro |
|---|---|
| `negro` | #341896 |
| `azul_noche` | #0030A8 |
| `marron_cafe` | #964000 |
| `gris_pizarra` | #005C7C |
| `morado_oscuro` | #5A0096 |
| `azul_electrico` | #0050FF |
| `violeta` | #8228FF |
| `naranja_atardecer` | #F05A00 |
| `rosa` | #C800A0 |
| `verde_esmeralda` | #008C5A |
| `rojo_vino` | #96002D |

Cada episodio varía solo las estrellas, la ciudad, las luces, el degradado y la música. Hay 8 estilos de música generada por código, distinta en cada vídeo.

## Publicar de un toque desde el iPhone

Con el atajo **Nuevo episodio** copias el guion corto, tocas el atajo y te devuelve el enlace al vídeo y a sus textos. Cómo montarlo: [ATAJO_IPHONE.md](ATAJO_IPHONE.md).

Junto a cada vídeo aparece `videos/<id>_textos.txt`, con el texto para Facebook y el título, la descripción y los hashtags para YouTube, en inglés. Al final de cada parte va un producto de Amazon según la lección (tienda e ID en [`config/amazon.txt`](config/amazon.txt)), con el aviso de afiliado.

## Personajes

- **Muñequitos de palo:** el Hacedor y el Perfeccionista. Pueden ir en pantalla partida (arriba y abajo) o juntos en una escena única.
- **Objetos con vida:** martillos con cara (desde el episodio 3). Los personajes son siempre blancos, con cara de puntos y sonrisa.

Todas las piezas que se pueden usar desde el JSON están en [GUIA_GUIONES.md](GUIA_GUIONES.md).

## Tu propia música

Sube un archivo `musica.mp3` a la carpeta [`audio/`](audio/LEEME.md). Si no hay ninguno, se usa la música generada por código.

## Comprobaciones automáticas

En cada render se comprueba:
- H.264 perfil High, yuv420p, 1080x1920 y 30 fps constantes.
- Audio AAC a 48 kHz en estéreo, y `+faststart`.
- Ningún fotograma en negro (`blackdetect d=0.03 pix_th=0.10`).
- Que el último fotograma empalme con el primero, para que el bucle no se note.

## Para desarrollo (ordenador)

```bash
pip install -r requirements.txt   # necesita ffmpeg instalado
python -m pytest -q
python -m dnp.render episodios/ep01_la_silla.json --capturas 0,8,16
python -m dnp.publicar --todos --solo-comprobar   # lo mismo que hace el workflow, sin publicar
python tests/referencias/regenerar.py             # solo si cambias el dibujo a propósito
```

El código: `dnp/escena.py` (escenas y ambiente), `dnp/piezas.py` (objetos), `dnp/actores.py` (personajes y acciones), `dnp/guion.py` (esquema del JSON y validación), `dnp/motor.py` (rebobinado, bucle, textos) y `dnp/publicar.py` (publicación y `ERRORES.txt`).
