# Done, not perfect

Serie de vídeos cortos sin voz con dos muñequitos de palo: el **Perfeccionista** (gafas y lápiz en la oreja), que nunca termina, y el **Hacedor**, que lo hace imperfecto pero lo termina.

Todo se genera por código en GitHub Actions: dibujo, animación, música y efectos de sonido.

## Generar un episodio desde el iPhone

1. Abre el repositorio en Safari o en la app de GitHub y ve a **Actions**.
2. Elige **Render episodio** y pulsa **Run workflow**. Escoge el episodio en el desplegable y vuelve a pulsar el botón verde **Run workflow**.
3. Espera unos 2 minutos hasta que salga la marca verde ✅.
4. Abre el enlace de descarga directa del episodio:
   - Ep. 1: https://github.com/solertemplates/done-not-perfect/raw/main/videos/ep01_la_silla.mp4
   - Ep. 2: https://github.com/solertemplates/done-not-perfect/raw/main/videos/ep02_la_escalera.mp4
   - Ep. 3: https://github.com/solertemplates/done-not-perfect/raw/main/videos/ep03_los_dos_martillos.mp4
   - Ep. 4: https://github.com/solertemplates/done-not-perfect/raw/main/videos/ep04_la_roca.mp4

   También lo tienes en el resumen de la ejecución y en la carpeta [`videos/`](videos/). Pulsa compartir y elige **Guardar vídeo** para llevarlo a Fotos.
5. La miniatura (el primer fotograma) está al lado, en `videos/<episodio>_miniatura.png`.

Cada ejecución que pasa todas las comprobaciones guarda el vídeo en la carpeta `videos/` de `main` y sustituye al anterior. Las versiones anteriores quedan en el historial del archivo. Si alguna comprobación falla, la ejecución sale en rojo ❌, no se toca `videos/` y el vídeo queda en **Artifacts**, al final de la página de la ejecución, para revisarlo.

## Crear episodios solo con JSON

Desde el episodio 4 se pueden crear episodios sin programar, con un bloque `"guion"` en el JSON. Ahí se eligen la escena, los personajes, las herramientas, los objetos, las acciones y los contadores. Todo está explicado en [GUIA_GUIONES.md](GUIA_GUIONES.md).

## Cambiar textos o tiempos

Edita `episodios/ep01_la_silla.json` desde la web de GitHub (icono del lápiz) y vuelve a lanzar el workflow. Si hay un error, aparece explicado en español en el registro de la ejecución, por ejemplo: `Falta el campo obligatorio 'textos.cierre'`.

> Truco: el teclado del iPhone cambia `"` por `“ ”`, y eso rompe el JSON. Para evitarlo, desactiva **Ajustes > General > Teclado > Puntuación inteligente** mientras editas.

## Fondos

Cada episodio elige su fondo con el campo `"fondo"` del JSON. Solo se permiten estos, todos muy oscuros para que los personajes blancos resalten:

| `"fondo"` | Color |
|---|---|
| `negro` | #0E0F12 |
| `azul_noche` | #0D1424 |
| `marron_cafe` | #1A130E |
| `gris_pizarra` | #15181C |
| `morado_oscuro` | #171222 |

Las ventanas muestran estrellitas, algunas con un parpadeo muy suave. Las lámparas proyectan un cono de luz ámbar cálido: es luz de ambiente, no el amarillo de riesgo.

## Personajes

- **Muñequitos de palo** (episodios 1 y 2): pantalla partida, arriba el Hacedor y abajo el Perfeccionista.
- **Objetos con vida** (desde el episodio 3): cualquier objeto puede ser un personaje, siempre blanco y con cara de puntos y sonrisa. Para crear uno nuevo se define su forma en `dnp/objetos.py` (el martillo sirve de ejemplo).

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
```
