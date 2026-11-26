# Carpeta de audio

Aquí puedes subir **tu propia música** para los episodios.

- Llama al archivo `musica.mp3` (también vale `.m4a`, `.wav`, `.aac`, `.flac` u `.ogg`).
- Con `"musica": "auto"` en el JSON del episodio se usa tu archivo si existe; si no hay ninguno, se genera música por código.
- Para usar un archivo concreto, pon su ruta en el JSON: `"musica": "audio/mi_cancion.mp3"`.
- Para forzar la música generada aunque haya archivos aquí: `"musica": "generada"`.

La música se recorta (o se repite) a la duración del vídeo, se suaviza la unión del bucle y se ajusta el volumen. Los efectos de sonido se siguen generando por código.

Subirlo desde el iPhone: en github.com abre esta carpeta → **Add file → Upload files**.
