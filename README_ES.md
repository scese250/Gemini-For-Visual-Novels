
Programita para leer novelas visuales con IA en Luna Translator.

## Consejo a tener en cuenta
Recomiendo encarecidamente que usen al menos dos cuentas de Google para evitar bloqueos temporales. El sistema rota las cuentas según el valor `rotation_batch_size` en `config.json` (por defecto cada 30 peticiones). Si les llegan a bloquear, pueden usar VPN. NO les van a banear la cuenta de Google, solo el uso de Gemini. 

## Requisitos

*   Python 3.8 o superior instalado.
*   Navegador **Firefox** o **Chrome** con sesión iniciada en Google.

## Instalación y Uso

Debes seguir este orden:

### 1. Instalación (Solo la primera vez)
Ejecuta el archivo `install.bat`. Este script se encargará de:
*   Crear un entorno virtual de Python.
*   Instalar todas las dependencias necesarias.

### 2. Iniciar Servidor
Una vez instalado, simplemente ejecuta `run.bat` para iniciar el servidor.

## Configuración de Cookies
El script utiliza exclusivamente `Cookies.txt` para la autenticación. La lectura automática del navegador se ha desactivado por estabilidad.

Para usuarios de Chrome, Firefox o cualquier navegador basado en Chromium, sigue estos pasos:

1.  Instala la extensión **Cookie-Editor** en tu navegador.
    *   [Chrome Web Store](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)
    *   [Firefox Add-ons](https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/)
2.  Entra a `google.com` (o `gemini.google.com`) y asegúrate de estar logueado.
3.  Abre la extensión **Cookie-Editor**.
4.  Haz clic en el botón **Export** (abajo a la derecha) y selecciona **Export as JSON**.
5.  Crea un archivo nuevo llamado `Cookies.txt` dentro de la carpeta `Gemini_Server_Release`.
6.  Pega el contenido JSON copiado dentro de `Cookies.txt` y guarda.

**Tip Multicuentas:**
Puedes pegar el JSON de varias cuentas diferentes en el mismo archivo `Cookies.txt`. Simplemente pega el JSON de la primera cuenta, haz un salto de línea, y pega el siguiente (o ponlos uno tras otro). El script detectará todas las cuentas válidas.

### ⚠️ IMPORTANTE: Cómo obtener cookies de varias cuentas
*   **Solo 1 cuenta por navegador/perfil:** Si tienes varias sesiones de Google abiertas en el mismo navegador (ej. cambiar de cuenta en Gmail), la exportación **SOLO tomará la cuenta principal** (la primera).
*   **Solución:** Para obtener las cookies de tus cuentas secundarias, debes iniciar sesión en un **Perfil de Navegador Nuevo** o usar un **Navegador Diferente**.
*   **NO uses Incógnito:** Las cookies obtenidas en modo Incógnito caducan muy rápido o al cerrar la ventana, por lo que dejarán de funcionar casi de inmediato. Usa siempre ventanas normales.

## Endpoints

*   **POST** `http://127.0.0.1:8000/v1/chat/completions`: Endpoint compatible con Luna Translator.
*   **GET** `http://127.0.0.1:8000/v1/models`: Lista de modelos disponibles.
    *   *Nota: Soporte para Gemini 3.0 Flash, 3.0 Flash Thinking y 3.0 Pro.*

## Funciones Avanzadas: Context Awareness (Memoria de Escena)

Esta versión incluye un **Sistema de Contexto Avanzado** que recuerda los detalles de la escena para mejorar la precisión de la traducción (evita confundir géneros o sujetos).

### Configuración (`config.json`)
*   `context_enabled`: (true/false) Activa o desactiva el sistema.
*   `context_model`: "flash" (rápido) o "pro" (mejor calidad) para el análisis de fondo.
*   `context_dedicated_account`: (true/false) Si es `true`, el sistema usará una **CUENTA DEDICADA** exclusivamente para "pensar" el contexto, separada de las que traducen.

### Cómo usar una Cuenta Dedicada para Contexto
1.  Pon `"context_dedicated_account": true` en `config.json`.
2.  Crea un archivo llamado `Context.txt` en la carpeta raíz.
3.  Exporta las cookies de tu cuenta "Inteligente" (ej. una con suscripción Gemini Advanced/Pro) y pégalas en `Context.txt`.
4.  Reinicia el servidor.
*Si no existe `Context.txt`, el script creará una plantilla automáticamente.*

## Endpoints de Gestión
*   **GET** `/context/status`: Mira qué es lo que la IA "recuerda" de la escena actual.
*   **POST** `/context/reset`: Borra la memoria del contexto (útil al iniciar una nueva ruta o juego).
*   **GET** `/cookies/status`: Verifica el estado de las cuentas cargadas.
*   **POST** `/cookies/reload`: Recarga `Cookies.txt` sin cerrar el servidor.
    
## Cómo debes configurar Luna Trasnlator

<img width="861" height="657" alt="image" src="https://github.com/user-attachments/assets/97f936ff-2fcc-4f84-a1a6-630e67a9a761" />



