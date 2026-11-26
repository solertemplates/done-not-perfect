# Done, not perfect

Serie de vídeos cortos sin voz con dos muñequitos de palo: el **Perfeccionista** (gafas y lápiz en la oreja), que nunca termina, y el **Hacedor**, que lo hace imperfecto pero lo termina.

Todo se genera por código en GitHub Actions: dibujo, animación, música y efectos de sonido.

## Generar un episodio desde el iPhone

1. Abre el repositorio en Safari o en la app de GitHub y ve a **Actions**.
2. Elige **Render episodio** y pulsa **Run workflow**. Deja el episodio que viene por defecto y vuelve a pulsar **Run workflow**.
3. Espera unos 2 minutos hasta que salga la marca verde ✅ y abre esa ejecución.
4. Abajo, en **Artifacts**, descarga **episodio**. Es un `.zip` con:
   - `ep01_la_silla.mp4`: el vídeo (1080x1920, 30 fps, H.264 + AAC).
   - `miniatura.png`: el primer fotograma, para usarlo de portada.
   - `informe.txt`: el resultado de las comprobaciones.
5. En la app **Archivos**, toca el `.zip` para descomprimirlo. Luego abre el MP4, pulsa compartir y elige **Guardar vídeo** para llevarlo a Fotos.

El resumen de la ejecución muestra todas las comprobaciones. Si alguna falla, la ejecución sale en rojo ❌, pero el vídeo se sube igualmente para que puedas revisarlo.

## Cambiar textos o tiempos

Edita `episodios/ep01_la_silla.json` desde la web de GitHub (icono del lápiz) y vuelve a lanzar el workflow. Si hay un error, aparece explicado en español en el registro de la ejecución, por ejemplo: `Falta el campo obligatorio 'textos.cierre'`.

> Truco: el teclado del iPhone cambia `"` por `“ ”`, y eso rompe el JSON. Para evitarlo, desactiva **Ajustes > General > Teclado > Puntuación inteligente** mientras editas.

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
