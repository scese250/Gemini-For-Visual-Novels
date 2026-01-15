## [SI ERES LATINO CLICK ACÁ](https://github.com/scese250/Gemini-For-Visual-Novels/blob/main/README_ES.md)

This script launches a local server compatible with LunaTranslator (chat/completions) that uses EXCLUSIVELY your browser sessions (Cookies) to interact with Google Gemini.

**Why only Cookies?**
Free API keys have very low requests per minute (RPM) limits. By using browser sessions (Firefox/Chrome), we can access models like Gemini 3.0 Pro/Flash with much more relaxed limits.

## Important Recommendation: Avoid Soft Bans
The system automatically rotates accounts every **10 requests**.
**IT IS HIGHLY RECOMMENDED to have at least 2 Google accounts setup in the Cookies.txt so the script can switch between them. This distributes the load and prevents temporary blocks (soft bans) due to excessive usage on a single account.

## Requirements

*   Python 3.8 or higher installed.
*   **Firefox** or **Chrome** browser with a logged-in Google session.

## Installation and Usage

### 1. Installation
Run the `install.bat` file. This script will handle:
*   Creating a Python virtual environment.
*   Installing all necessary dependencies.

### 2. Start Server
Once installed, simply run `run.bat` to start the server.

## Cookie Configuration
### Option A: Automatic (Firefox Only)
If you use **Firefox**, the script will attempt to read cookies automatically. You don't need to do anything else.
*Note: Automatic reading DOES NOT work with Chrome/Edge/Any Chromium browser based due to security restrictions.*

### Option B: Manual (Chrome, Edge, Brave, etc.) - RECOMMENDED

1.  Install the **Cookie-Editor** extension in your browser.
    *   [Chrome Web Store](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)
    *   [Firefox Add-ons](https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/)
2.  Go to `google.com` (or `gemini.google.com`) and make sure you are logged in.
3.  Open the **Cookie-Editor** extension.
4.  Click the **Export** button (bottom right) and select **Export as JSON**.
5.  Create a new file named `Cookies.txt` in the root folder.
6.  Paste the copied JSON content into `Cookies.txt` and save.

**Multi-Account Tip:**
You can paste the JSON from multiple different accounts into the same `Cookies.txt` file. Simply paste the JSON of the first account, add a line break, and paste the next one (or just append them). The script will detect all valid accounts.

### ⚠️ IMPORTANT: How to get cookies from multiple accounts
*   **Only 1 account per browser/profile:** If you have multiple Google sessions open in the same browser (e.g., switching accounts in Gmail), the export will **ONLY take the main account** (the first one).
*   **Solution:** To get cookies from your secondary accounts, you must log in using a **New Browser Profile** or use a **Different Browser**.
*   **DO NOT use Incognito:** Cookies obtained in Incognito mode expire very quickly or when the window is closed, so they will stop working almost immediately. Always use normal windows.

## Endpoints

*   **POST** `http://127.0.0.1:8000/v1/chat/completions`: LunaTranslator compatible endpoint.
*   **GET** `http://127.0.0.1:8000/v1/models`: List of available models.
    *   *Note: Although `gemini-2.5-flash` appears in the list (for compatibility), the system internally uses the **Gemini 3.0 Flash** web model.*

## Luna Translator config example

<img width="861" height="657" alt="image" src="https://github.com/user-attachments/assets/7d605c9d-8e6d-403f-9e5f-f76bf0297d86" />






