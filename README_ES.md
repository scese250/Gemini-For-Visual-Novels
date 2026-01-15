
Programita para leer novelas visuales con IA en Luna Translator.

## Consejo a tener en cuenta
Recomiendo encarecidamente que usen dos cuentas de Google para evitar que les bloqueen (temporalmente) el uso de Gemini. Si les llegan a bloquear, pueden usar VPN. NO les van a banear la cuenta de Google, solo el uso de Gemini. 

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
### Opción A: Automática (Solo Firefox)
Si usas **Firefox**, el script intentará leer las sesión automáticamente. No necesitas hacer nada más.
*Nota: NO funciona con Chrome/Edge debido a restricciones de seguridad.*

### Opción B: Manual (Chrome, Edge, Brave, etc.) - RECOMENDADO
Para usuarios de Chrome o si la opción automática falla, sigue estos pasos:

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
    *   *Nota: Aunque en la lista aparezca `gemini-2.5-flash` (por compatibilidad), el sistema utiliza internamente el modelo **Gemini 3.0 Flash** de la web.*
    
## Cómo debes configurar Luna Trasnlator

<img width="861" height="657" alt="image" src="https://github.com/user-attachments/assets/97f936ff-2fcc-4f84-a1a6-630e67a9a761" />



