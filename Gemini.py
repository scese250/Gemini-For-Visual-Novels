# --- START OF FILE Gemini.py ---

import asyncio
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import time
import re
import os
import json
import random

import threading


# --- IMPORTACIÓN DE DEPENDENCIAS ---
try:
    from gemini_webapi import GeminiClient, UsageLimitExceeded, TemporarilyBlocked, ModelInvalid
except ImportError:
    print("[ERROR] Error: Install gemini-webapi (pip install gemini-webapi)")
    exit(1)

# --- CONFIGURATION ---
def load_config():
    """Load configuration from config.json"""
    default_config = {
        "context_enabled": False,
        "context_model": "flash",
        "rotation_batch_size": 30,
        "context_update_interval": 20,
        "context_dedicated_account": False
    }
    
    if os.path.exists("config.json"):
        try:
            with open("config.json", 'r', encoding='utf-8') as f:
                content = f.read()
                # Remove comments (lines starting with // or inline //) to avoid JSON errors
                content_clean = re.sub(r'//.*', '', content)
                config = json.loads(content_clean)
                
                # Merge with defaults
                for key in default_config:
                    if key not in config:
                        config[key] = default_config[key]
                print(f"✅ [CONFIG] Configuration loaded: {config}")
                return config
        except Exception as e:
            print(f"⚠️ [CONFIG] Error loading config.json: {e}. Using defaults.")
    else:
        try:
            with open("config.json", 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4)
            print(f"✅ [CONFIG] Created config.json with default values (context_enabled=False).")
        except Exception as e:
            print(f"❌ [CONFIG] Failed to create config.json: {e}")
    
    return default_config

CONFIG = load_config()


# --- CONTEXT MANAGER (Detailed Scene Context) ---
class ContextManager:
    """
    Manages a separate AI chat for generating detailed scene context summaries.
    - Uses Gemini 3.0 Pro in a continuous chat
    - Updates context every N lines (configurable)
    - Non-blocking: context generation runs in background
    """
    def __init__(self, update_interval: int = 20):
        self.update_interval = update_interval  # Lines before context update
        self.lines_buffer: List[str] = []       # Accumulated lines since last update
        self.all_lines: List[str] = []          # All lines for reference
        self.current_context: str = ""           # Current detailed context
        self.context_lock = threading.Lock()
        self.is_updating = False
        self.line_count = 0
        self.context_chat = None                 # Dedicated chat for context generation
        self._initialized = False
        
    async def initialize(self, cookie_manager, model="flash"):
        """Initialize the context generation chat using the existing connected client."""
        try:
            if not cookie_manager.accounts:
                print("[CONTEXT] No accounts available for context manager")
                return False
            
            # Check for Dedicated Context Account (Context.txt)
            if CONFIG.get("context_dedicated_account", False):
                if not os.path.exists("Context.txt"):
                    print("⚠️ [CONTEXT] 'context_dedicated_account' is TRUE but Context.txt not found. Creating template.")
                    explanation = """[
    // PASTE YOUR DEDICATED ACCOUNT COOKIES HERE (JSON FORMAT)
    // Recommended: Use a Google account with Gemini Advanced (Pro) subscription for best context analysis.
    // Ensure "context_model" in config.json is set to "pro" to fully utilize this.
]"""
                    with open("Context.txt", 'w', encoding='utf-8') as f: f.write(explanation)
                    print("📝 [CONTEXT] Context.txt created. Please add your dedicated cookie and restart.")
                    # Fallback to shared for now
                    client = cookie_manager.get_client()
                else:
                    print("🌟 [CONTEXT] Using DEDICATED account from Context.txt")
                    try:
                        client = await self._load_dedicated_client()
                        if not client: raise Exception("Could not connect to dedicated account")
                    except Exception as e:
                        print(f"⚠️ [CONTEXT] Failed to load dedicated account: {e}. Falling back to shared rotation.")
                        client = cookie_manager.get_client()
            else:
                # Standard shared mode (uses current rotation account)
                client = cookie_manager.get_client()
            
            if not client:
                print("[CONTEXT] No connected client available yet. Will retry when first translation is made.")
                return False
            
            # Start a dedicated chat for context analysis (same client, different chat)
            # Use the model from config
            context_model = "gemini-3.0-flash" if model.lower() == "flash" else "gemini-3.0-pro"
            self.context_chat = client.start_chat(model=context_model)
            print(f"📖 [CONTEXT] Using model: {context_model}")
            
            # Initialize with system instructions
            init_prompt = """Eres un analizador de contexto para traducción de novelas visuales/juegos.
Tu trabajo es mantener un resumen ACTUALIZADO de lo que está pasando en la escena.

Cuando te envíe líneas de diálogo, debes responder con un resumen estructurado que incluya:
1. **ESCENA ACTUAL**: Descripción breve del lugar/situación
2. **PERSONAJES PRESENTES**: Quiénes están en la escena y sus posiciones (ej: "dentro del armario", "en la puerta")
3. **ACCIONES RECIENTES**: Qué acaba de pasar (quién hizo qué)
4. **TONO/AMBIENTE**: El mood de la escena (romántico, tenso, cómico, etc.)
5. **CONTEXTO IMPORTANTE**: Cualquier detalle relevante para entender las siguientes líneas

Mantén el resumen CONCISO pero INFORMATIVO. Máximo 150 palabras.
Responde SOLO con el resumen, sin explicaciones adicionales."""

            await self.context_chat.send_message(init_prompt)
            self._initialized = True
            print("✅ [CONTEXT] Context Manager initialized (sharing client, dedicated chat)")
            return True
            
        except Exception as e:
            print(f"❌ [CONTEXT] Failed to initialize context manager: {e}")
            return False
    async def _load_dedicated_client(self):
        """Load and connect the isolated context account from Context.txt"""
        try:
            with open("Context.txt", 'r', encoding='utf-8') as f: content = f.read()
            # Simple list parsing similar to Cookies.txt
            if "[" in content:
                data = json.loads(content)
                # If wrapped in list (Cookies.txt format)
                if isinstance(data, list):
                    # Handle flat list or list of lists
                    if data and isinstance(data[0], list): data = data[0] # Take first block if multiple
                
                psid = next((c['value'] for c in data if c['name'] == "__Secure-1PSID"), None)
                psidts = next((c['value'] for c in data if c['name'] == "__Secure-1PSIDTS"), None)
                
                if psid:
                    print(f"🔑 [CONTEXT] Found credentials in Context.txt. Connecting...")
                    client = GeminiClient(secure_1psid=psid, secure_1psidts=psidts)
                    await client.init(timeout=60, auto_close=False, auto_refresh=False)
                    return client
            return None
        except Exception as e:
            print(f"❌ [CONTEXT] Error reading Context.txt: {e}")
            return None

    def _is_valid_line(self, line: str) -> bool:
        """Check if a line should be added to context (filter noise)."""
        if not line:
            return False
        
        stripped = line.strip()
        
        # Filter empty lines
        if not stripped:
            return False
        
        # Filter lines that are only punctuation/pauses
        # Matches: "...", "…", "。。。", "・・・", "――", "──", etc.
        noise_patterns = [
            r'^[\.\…。・\-―─　\s]+$',  # Only dots, dashes, spaces
            r'^[\.]{2,}$',              # Multiple periods
            r'^…+$',                     # Ellipsis
            r'^[\s]*$',                  # Only whitespace
        ]
        for pattern in noise_patterns:
            if re.match(pattern, stripped):
                return False
        
        # Very short lines that are likely noise (less than 2 meaningful chars)
        if len(stripped) <= 1:
            return False
            
        return True
    
    def add_line(self, line: str):
        """Add a translated line to the buffer (with duplicate and noise filtering)."""
        with self.context_lock:
            # Filter invalid/noise lines
            if not self._is_valid_line(line):
                return
            
            # Filter duplicates: check if same as last line (regeneration)
            if self.all_lines and self.all_lines[-1] == line:
                return
            
            # Also check if it exists in recent buffer (last 5 lines)
            if line in self.lines_buffer[-5:] if len(self.lines_buffer) >= 5 else line in self.lines_buffer:
                return
            
            self.lines_buffer.append(line)
            self.all_lines.append(line)
            self.line_count += 1
            
            # Check if we need to trigger a context update
            if len(self.lines_buffer) >= self.update_interval and not self.is_updating:
                # Trigger async update in background
                lines_to_process = self.lines_buffer.copy()
                self.lines_buffer = []
                asyncio.create_task(self._update_context_async(lines_to_process))
    
    async def _update_context_async(self, lines: List[str]):
        """Update context in background without blocking translations."""
        if not self._initialized or not self.context_chat:
            return
            
        self.is_updating = True
        try:
            # Format lines for context analysis
            lines_text = "\n".join([f"{i+1}. {line}" for i, line in enumerate(lines)])
            
            # Get the previous context for better feedback/continuity
            previous_context = self.get_context()
            
            # Build the update prompt with previous context for better continuity
            if previous_context:
                prompt = f"""### CONTEXTO PREVIO (tu análisis anterior):
{previous_context}

### NUEVAS LÍNEAS DE DIÁLOGO ({len(lines)} líneas):
{lines_text}

Basándote en tu análisis previo y estas nuevas líneas, ACTUALIZA el resumen del contexto de la escena.
Mantén la coherencia con lo anterior, pero incorpora los nuevos eventos, cambios de escena, o desarrollo de personajes.
Recuerda incluir: escena actual, personajes y sus posiciones, acciones recientes, tono/ambiente, y contexto importante.
Máximo 150 palabras. Solo el resumen, sin explicaciones."""
            else:
                # First context generation (no previous context)
                prompt = f"""### PRIMERAS LÍNEAS DE DIÁLOGO ({len(lines)} líneas):
{lines_text}

Analiza estas líneas y genera el primer resumen del contexto de la escena.
Incluye: escena actual, personajes y sus posiciones, acciones recientes, tono/ambiente, y contexto importante.
Máximo 150 palabras. Solo el resumen, sin explicaciones."""

            response = await self.context_chat.send_message(prompt)
            
            if response and response.text:
                with self.context_lock:
                    self.current_context = response.text.strip()
                print(f"🔄 [CONTEXT] Updated scene context (processed {len(lines)} lines, total: {self.line_count})")
                
        except Exception as e:
            print(f"❌ [CONTEXT] Error updating context: {e}")
        finally:
            self.is_updating = False
    
    def get_context(self) -> str:
        """Get the current detailed context (non-blocking)."""
        with self.context_lock:
            return self.current_context
    
    def reset(self):
        """Reset the context manager for a new session."""
        with self.context_lock:
            self.lines_buffer = []
            self.all_lines = []
            self.current_context = ""
            self.line_count = 0








# --- SESSION MANAGER (COOKIES) ---
class CookieSessionManager:
    def __init__(self):
        self.accounts = [] 
        self.current_index = 0

    def add_account(self, source, psid, psidts):
        if not psid: return
        for acc in self.accounts:
            if acc['1PSID'] == psid: return
        self.accounts.append({'source': source, '1PSID': psid, '1PSIDTS': psidts, 'client': None})

    def _write_clean_cookies(self, accounts: list):
        """Rewrite Cookies.txt with only the essential cookies in a clean format."""
        try:
            clean_blocks = []
            for acc in accounts:
                # Create minimal cookie entries
                clean_cookies = [
                    {"name": "__Secure-1PSID", "value": acc["psid"], "domain": ".google.com"},
                    {"name": "__Secure-1PSIDTS", "value": acc["psidts"], "domain": ".google.com"} if acc["psidts"] else None
                ]
                # Remove None entries
                clean_cookies = [c for c in clean_cookies if c is not None]
                clean_blocks.append(json.dumps(clean_cookies, indent=2))
            
            # Write clean file
            with open("Cookies.txt", 'w', encoding='utf-8') as f:
                f.write("\n\n".join(clean_blocks))
            
            print(f"🧹 [CLEANUP] Cookies.txt cleaned. Kept only essential cookies for {len(accounts)} account(s).")
        except Exception as e:
            print(f"[WARNING] Could not clean Cookies.txt: {e}")

    def load_all(self):
        # 1. Firefox removed. Only load from Cookies.txt (Manual mode)
        cleaned_accounts = []  # For rewriting clean file
            

        


        # 3. File
        if os.path.exists("Cookies.txt"):
            try:
                with open("Cookies.txt", 'r', encoding='utf-8') as f: content = f.read()
                blocks = []
                # ... (rest of parsing logic)
                depth = 0
                start = 0
                for i, char in enumerate(content):
                    if char == '[':
                        if depth == 0: start = i
                        depth += 1
                    elif char == ']':
                        depth -= 1
                        if depth == 0: blocks.append(content[start:i+1])
                for index, block in enumerate(blocks):
                    try:
                        data = json.loads(block)
                        psid = next((c['value'] for c in data if c['name'] == "__Secure-1PSID"), None)
                        psidts = next((c['value'] for c in data if c['name'] == "__Secure-1PSIDTS"), None)
                        if psid: 
                            self.add_account(f"File_Account_{index+1}", psid, psidts)
                            # Store for clean file
                            cleaned_accounts.append({"psid": psid, "psidts": psidts})
                    except: continue
                
                # Rewrite Cookies.txt with only necessary cookies (clean format)
                if cleaned_accounts:
                    self._write_clean_cookies(cleaned_accounts)
            except Exception as e: print(f"[ERROR] Cookies.txt: {e}")
        else:
            # File missing -> Create Guide Template
            print("⚠️ [INIT] Cookies.txt not found. Creating a template file...")
            template = """[
    // INSTRUCTIONS:
    // 1. Install 'Cookie-Editor' extension for Chrome/Firefox.
    // 2. Go to gemini.google.com and ensure you are logged in.
    // 3. Open Cookie-Editor -> Export -> Export as JSON.
    // 4. Paste the content HERE (replace this text).
    //
    // TIP: You can add multiple accounts! Just paste one JSON block after another.
    // The server also supports 'Hot-Reload': You can add more cookies to this file while the server is running 
    // and they will be picked up automatically or via the /cookies/reload endpoint.
]"""
            with open("Cookies.txt", 'w', encoding='utf-8') as f:
                f.write(template)
            print("📝 [INIT] Created 'Cookies.txt'. Please paste your cookies inside and restart (or hot-reload).")
        
        print(f"[INFO] {len(self.accounts)} Cookie Accounts loaded.")

    async def connect_current(self):
        if not self.accounts: return False
        acc = self.accounts[self.current_index]
        if acc.get('client'):  # Ya está conectada
            return True
        try:
            client = GeminiClient(secure_1psid=acc['1PSID'], secure_1psidts=acc['1PSIDTS'])
            await client.init(timeout=120, auto_close=False, auto_refresh=False)
            acc['client'] = client
            return True
        except: return False
    
    async def connect_all(self):
        """Connect all accounts at startup to avoid delays during rotation."""
        if not self.accounts: return 0
        
        connected = 0
        
        # Connect each account sequentially to avoid conflicts with shared resources/browser-cookie3
        for i, acc in enumerate(self.accounts):
            if acc.get('client'):  # Skip if already connected
                connected += 1
                continue
            
            try:
                # Add a small delay between connections to be safe
                if i > 0:
                    await asyncio.sleep(2)
                    
                client = GeminiClient(secure_1psid=acc['1PSID'], secure_1psidts=acc['1PSIDTS'])
                await client.init(timeout=120, auto_close=False, auto_refresh=False)
                acc['client'] = client
                print(f"✅ [COOKIE] Account #{i + 1} ({acc['source']}) connected successfully")
                connected += 1
            except Exception as e:
                print(f"❌ [COOKIE] Account #{i + 1} ({acc['source']}) failed to connect: {e}")
        
        return connected

    def get_client(self):
        if not self.accounts: return None
        return self.accounts[self.current_index].get('client')

    async def rotate(self):
        if not self.accounts: return
        self.current_index = (self.current_index + 1) % len(self.accounts)
        print(f"🔄 [COOKIE] Rotating to Account #{self.current_index + 1}")
        # No need to connect - all accounts are pre-connected
        # Just verify the client is still valid
        if not self.get_client():
            print(f"⚠️ [COOKIE] Account #{self.current_index + 1} disconnected, reconnecting...")
            await self.connect_current()


# --- COOKIE ROTATION MANAGER ---
class RotationManager:
    """
    Cookie Rotation System:
    - Rotates account every N requests to avoid soft bans.
    - Configuration is loaded from config.json.
    """
    def __init__(self, batch_size=10):
        self.cookie_manager = CookieSessionManager()
        self.request_count = 0 
        self.BATCH_SIZE = batch_size  # Peticiones antes de rotar cuenta
        self.total_requests = 0
        self.is_rotating = False  # Flag to prevent race conditions

    async def initialize(self):
        self.cookie_manager.load_all()
        # Connect ALL accounts at startup instead of just the current one
        connected = await self.cookie_manager.connect_all()
        print(f"✅ [INIT] System initialized. Accounts detected: {len(self.cookie_manager.accounts)}")
        print(f"✅ [INIT] Connected accounts: {connected}/{len(self.cookie_manager.accounts)}")
        print(f"📋 [CONF] Rotation: Every {self.BATCH_SIZE} requests.")

    def increment_counter_sync(self):
        """Increment counter synchronously (no blocking operations)."""
        self.total_requests += 1
        self.request_count += 1
        
        needs_rotation = False
        needs_reload = False
        
        # Check if mid-batch reload is needed
        if self.request_count == self.BATCH_SIZE // 2:
            needs_reload = True
        
        # Check if rotation is needed
        if self.request_count >= self.BATCH_SIZE:
            needs_rotation = True
            self.request_count = 0
        
        print(f"� [STATS] Segment requests: {self.request_count}/{self.BATCH_SIZE} | Total: {self.total_requests}")
        
        return needs_rotation, needs_reload
    
    async def wait_if_rotating(self):
        """Wait if a rotation is in progress (prevents race conditions)."""
        if self.is_rotating:
            print("⏳ [WAIT] Rotation in progress, waiting...")
            while self.is_rotating:
                await asyncio.sleep(0.1)
            print("✅ [WAIT] Rotation complete, proceeding.")
    
    async def do_background_tasks(self, needs_rotation: bool, needs_reload: bool):
        """Perform rotation/reload in background without blocking response."""
        # Auto-reload cookies at mid-batch
        if needs_reload:
            old_count = len(self.cookie_manager.accounts)
            self.cookie_manager.load_all()
            new_count = len(self.cookie_manager.accounts)
            if new_count > old_count:
                print(f"🍪 [AUTO-RELOAD] Detected {new_count - old_count} new cookie account(s)! Total: {new_count}")
        
        # Rotate account in background
        if needs_rotation:
            self.is_rotating = True
            try:
                print(f"🔄 [ROTATION] Limit of {self.BATCH_SIZE} requests reached. Rotating in background...")
                await self.cookie_manager.rotate()
            finally:
                self.is_rotating = False


# --- GLOBAL VARS ---
app = FastAPI()

@app.middleware("http")
async def log_process_time(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    client = f"{request.client.host}:{request.client.port}" if request.client else "unknown"
    # Status phrase simple mapping (optional, 'OK' hardcoded to match user request mostly)
    status_phrase = "OK" if response.status_code == 200 else "Error"
    
    print(f"INFO:     {client} - \"{request.method} {request.url.path} HTTP/1.1\" {response.status_code} {status_phrase} ({process_time:.2f}s)")
    
    return response
rotation_manager = RotationManager(batch_size=CONFIG["rotation_batch_size"])
context_manager = ContextManager(update_interval=CONFIG["context_update_interval"])

# --- STATE ---
# Only for Cookies, official API is stateless
THREAD_STATE: Dict[int, Dict[str, Any]] = {}

# --- MODELS ---
class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = "gemini-3.0-flash"
    messages: List[Message]
    stream: Optional[bool] = False

# --- UTILS ---
def clean_response(text: str) -> str:
    if not text: return ""
    # Priority: If there is a code block, extract ONLY its content
    match = re.search(r'```(?:json|xml|text|txt)?\s*(.*?)\s*```', text, flags=re.DOTALL)
    if match:
        text = match.group(1)
    
    # Standard additional cleanup
    patterns = [r"^Here is the translation:?\s*", r"^Translation:?\s*", r"^La traducción es:?\s*"]
    for p in patterns: text = re.sub(p, "", text, flags=re.IGNORECASE)
    text = re.sub(r'\[\d+\]', '', text)
    text = text.strip()
    if text.startswith('"') and text.endswith('"') and len(text) > 2: text = text[1:-1]
    return text.strip()

# --- STARTUP ---
@app.on_event("startup")
async def startup_event():
    await rotation_manager.initialize()
    # Initialize context manager with the cookie manager
    if CONFIG["context_enabled"]:
        success = await context_manager.initialize(rotation_manager.cookie_manager, model=CONFIG["context_model"])
        if success:
            print("📖 [CONTEXT] Scene context system ready (updates every 20 lines)")
        else:
            print("⚠️ [CONTEXT] Context system not initialized. Will work without detailed context.")
    else:
        print("🚫 [CONTEXT] Context system disabled by config.json")

# --- CORE LOGIC ---
async def execute_query(full_prompt: str, model_id_request: str):
    
    # Total attempts before giving up
    max_retries = 3 
    
    for attempt in range(max_retries):
        
        try:
            response_text = ""
            
            # Wait if a rotation is in progress (prevents race conditions)
            await rotation_manager.wait_if_rotating()
            
            # --- COOKIE MODE ONLY ---
            cm = rotation_manager.cookie_manager
            client = cm.get_client()
            
            if not client:
                if not await cm.connect_current(): 
                    # If connection fails, force rotate and retry loop
                        await cm.rotate()
                        continue
            
            # Setup Chat
            acc_idx = cm.current_index
            
            model_id_lower = model_id_request.lower()
            if "thinking" in model_id_lower:
                target_model = "gemini-3.0-flash-thinking"
            elif "flash" in model_id_lower:
                target_model = "gemini-3.0-flash"
            else:
                target_model = "gemini-3.0-pro"
            
            if acc_idx not in THREAD_STATE: THREAD_STATE[acc_idx] = {}
            chat = THREAD_STATE[acc_idx].get(target_model)
            
            if not chat:
                chat = client.start_chat(model=target_model)
                THREAD_STATE[acc_idx][target_model] = chat
            
            print(f"--> [COOKIE Request #{rotation_manager.request_count + 1}/{rotation_manager.BATCH_SIZE}] Account #{acc_idx+1} | Requested: {model_id_request} -> Using: {target_model}")
            
            resp_obj = await chat.send_message(full_prompt)
            if resp_obj and resp_obj.text:
                response_text = resp_obj.text
            else:
                raise Exception("Empty Response (Cookie)")

            # SUCCESS - Increment counter synchronously (non-blocking)
            needs_rotation, needs_reload = rotation_manager.increment_counter_sync()
            
            # Schedule background tasks (rotation/reload) without blocking response
            if needs_rotation or needs_reload:
                asyncio.create_task(rotation_manager.do_background_tasks(needs_rotation, needs_reload))
            
            return clean_response(response_text)

        except (UsageLimitExceeded, TemporarilyBlocked) as e:
            print(f"🛑 [COOKIE] Rate Limit/Blocked detected: {e}. Rotating immediately...")
            # Clear chat state for this blocked account
            THREAD_STATE[rotation_manager.cookie_manager.current_index] = {}
            await rotation_manager.cookie_manager.rotate()
            time.sleep(1) # Brief pause

        except Exception as e:
            err_str = str(e)
            print(f"❌ [COOKIE] Generic Error: {err_str}")
            
            # Legacy check just in case
            if "429" in err_str or "Invalid response" in err_str:
                print("⚠️ Cookie Rate Limit (Legacy Check). Rotating account...")
                THREAD_STATE[rotation_manager.cookie_manager.current_index] = {}
                await rotation_manager.cookie_manager.rotate()
            else:
                # For other errors, also rotate to be safe
                await rotation_manager.cookie_manager.rotate()
            
            time.sleep(1)

    raise HTTPException(status_code=500, detail="Gemini: All methods failed (Cookie).")


# --- ENDPOINTS ---
@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    system_instruction = ""
    previous_user_lines = []
    current_msg = ""
    
    # Extract messages by role
    for msg in request.messages:
        content = msg.content.strip()
        if not content: continue
        
        if msg.role == "system":
            system_instruction = content
        elif msg.role == "user":
            previous_user_lines.append(content)
        # We deliberately ignore 'assistant' messages (previous translations) 
        # based on user request to only show Japanese context.
            
    # The last user message is the current target/instruction
    if previous_user_lines:
        current_msg = previous_user_lines.pop()
        
    # Build final prompt with NEW FORMAT:
    # [Prompt del usuario]
    # [Context prior to sentence]
    # [Contexto detallado]  <-- NEW: AI-generated scene context
    # [Texto a traducir]
    prompt_parts = []
    
    # 1. System Prompt (User's prompt/instructions)
    if system_instruction:
        prompt_parts.append(system_instruction)
        
    # 2. Context prior to sentence (Previous Japanese lines)
    if previous_user_lines:
        ctx_block = ["### Context prior to sentence:"]
        for i, line in enumerate(previous_user_lines):
            ctx_block.append(f"{i+1}. {line}")
        prompt_parts.append("\n".join(ctx_block))
    
    # 3. Detailed Scene Context (AI-generated, non-blocking)
    if CONFIG["context_enabled"]:
        detailed_context = context_manager.get_context()
        if detailed_context:
            prompt_parts.append(f"### Detailed Scene Context (AI Analysis):\n{detailed_context}")
    
    # 4. Text to translate (Current Message)
    if current_msg:
        prompt_parts.append("\n### TEXT TO TRANSLATE (DO NOT RETURN COMMENTS OR EXPLANATIONS):")
        # Explicit format instruction to avoid comments and facilitate copying
        prompt_parts.append("IMPORTANT: Put THE TRANSLATION inside a ``` code block for easy copying. All text outside this block will be ignored.")
        prompt_parts.append(current_msg)
         
    final_prompt = "\n\n".join(prompt_parts)

    answer = await execute_query(final_prompt, request.model)
    
    # Add the original line to context manager for future context updates
    # This runs in background, won't block the response
    if CONFIG["context_enabled"] and current_msg:
        context_manager.add_line(current_msg)
    
    return {
        "id": "chatcmpl-hybrid",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": answer}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": len(final_prompt), "completion_tokens": len(answer), "total_tokens": 0}
    }

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "gemini-3.0-flash", "object": "model", "owned_by": "google"},
            {"id": "gemini-3.0-flash-thinking", "object": "model", "owned_by": "google"},
            {"id": "gemini-3.0-pro", "object": "model", "owned_by": "google"}
        ]
    }

# --- CONTEXT MANAGEMENT ENDPOINTS ---
@app.get("/context/status")
async def context_status():
    """Get the current status of the scene context system."""
    return {
        "lines_processed": context_manager.line_count,
        "lines_in_buffer": len(context_manager.lines_buffer),
        "update_interval": context_manager.update_interval,
        "is_updating": context_manager.is_updating,
        "current_context": context_manager.get_context(),
        "initialized": context_manager._initialized
    }

@app.post("/context/reset")
async def context_reset():
    """Reset the context manager for a new scene/game session."""
    context_manager.reset()
    # Re-initialize the context chat
    await context_manager.initialize(rotation_manager.cookie_manager, model=CONFIG.get("context_model", "flash"))
    return {
        "status": "success",
        "message": "Context reset successfully. Ready for new scene."
    }

# --- COOKIE MANAGEMENT ENDPOINTS ---
@app.get("/cookies/status")
async def cookies_status():
    """Get the current status of cookie accounts."""
    cm = rotation_manager.cookie_manager
    accounts_info = []
    for i, acc in enumerate(cm.accounts):
        accounts_info.append({
            "index": i + 1,
            "source": acc['source'],
            "connected": acc.get('client') is not None,
            "is_current": i == cm.current_index
        })
    return {
        "total_accounts": len(cm.accounts),
        "current_index": cm.current_index + 1,
        "request_count": rotation_manager.request_count,
        "batch_size": rotation_manager.BATCH_SIZE,
        "total_requests": rotation_manager.total_requests,
        "accounts": accounts_info
    }

@app.post("/cookies/reload")
async def cookies_reload():
    """Reload cookies from Cookies.txt and browser without restarting the server."""
    cm = rotation_manager.cookie_manager
    old_count = len(cm.accounts)
    
    # Reload cookies (will add new ones, won't duplicate existing)
    cm.load_all()
    
    new_count = len(cm.accounts)
    added = new_count - old_count
    
    # If we added new accounts and current one is not connected, try to connect
    if added > 0 and not cm.get_client():
        await cm.connect_current()
    
    return {
        "status": "success",
        "message": f"Cookies reloaded. Added {added} new account(s).",
        "previous_count": old_count,
        "current_count": new_count,
        "accounts": [{"index": i+1, "source": acc['source']} for i, acc in enumerate(cm.accounts)]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, access_log=False)