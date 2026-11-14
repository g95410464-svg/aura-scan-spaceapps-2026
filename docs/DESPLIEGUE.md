# Preparar la publicación

La aplicación todavía no tiene un enlace público de producción. El contenedor propuesto sirve los archivos compilados de React y la API Python bajo el mismo origen.

## Host requerido

- Ejecución de contenedores Linux con Python y ONNX Runtime (una página estática en GitHub Pages no ejecuta este backend).
- HTTPS terminado por el host/proxy.
- Volumen persistente para capturas y, si se usa SQLite, también para su archivo de datos.
- PostgreSQL opcional mediante `DATABASE_URL`; debe probarse antes de anunciar compatibilidad operativa.
- CPU/memoria/concurrencia dimensionadas mediante mediciones sobre las imágenes previstas. El OCR se serializa dentro de cada proceso para evitar inferencia simultánea sobre el mismo motor.

## Variables

| Variable | Función |
|---|---|
| `DATABASE_URL` | SQLite persistente o PostgreSQL con psycopg. |
| `STORAGE_DIR` | Directorio privado de capturas; `/data/captures` en el contenedor. |
| `PUBLIC_ORIGIN` | Origen exacto autorizado: esquema, dominio y puerto si corresponde. |
| `SECURE_COOKIES` | `true` para HTTPS; `false` solo para desarrollo HTTP local. |
| `PORT` | Puerto que asigna el proveedor; 8000 por defecto. |

`.env.example` documenta variables; la aplicación no lee ese archivo automáticamente. Nunca subir un `.env` real ni incluir secretos en el frontend o la imagen del contenedor.

## Secuencia

1. Ejecutar pruebas y compilar la interfaz.
2. Construir `Dockerfile`; confirmar que los paquetes y los modelos OCR se cargan en el host.
3. Configurar almacenamiento, variables y HTTPS, sin incluir datos reales en la imagen.
4. Comprobar `/api/health` y completar registro → demostración → confirmación → historial → informe PDF.
5. Reiniciar el servicio y comprobar persistencia.
6. Verificar cuentas aisladas, denegación de cámara, imágenes ilegibles y errores de red.
7. Probar copia/restauración y definir retención/eliminación de capturas antes de habilitar datos reales.

No se ha contratado un proveedor ni se anuncian costos o capacidad sin comprobarlos. La limitación de intentos de login/captura es por proceso; varios workers o réplicas necesitan un limitador compartido y almacenamiento consistente.

## Evolución de esquema

El primer arranque crea las tablas ausentes. No modifica automáticamente tablas existentes. Antes de publicar nuevas versiones con cambios de esquema, añadir migraciones y respaldos; no borrar el volumen para resolver una actualización.
