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


# --- IMPORTACIÓN DE DEPENDENCIAS ---
try:
    from gemini_webapi import GeminiClient
except ImportError:
    print("[ERROR] Error: Install gemini-webapi (pip install gemini-webapi)")
    exit(1)

# Attempt to import browser_cookie3
try:
    import browser_cookie3
    BROWSER_COOKIES_AVAILABLE = True
except ImportError:
    BROWSER_COOKIES_AVAILABLE = False







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

    def load_all(self):
        # 1. Firefox
        if BROWSER_COOKIES_AVAILABLE:
            try:
                cj = browser_cookie3.firefox(domain_name=".google.com")
                c = {x.name: x.value for x in cj}
                self.add_account("Firefox", c.get("__Secure-1PSID"), c.get("__Secure-1PSIDTS"))
            except: pass
            

        


        # 3. File
        if os.path.exists("Cookies.txt"):
            try:
                with open("Cookies.txt", 'r', encoding='utf-8') as f: content = f.read()
                blocks = []
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
                        if psid: self.add_account(f"File_Account_{index+1}", psid, psidts)
                    except: continue
            except Exception as e: print(f"[ERROR] Cookies.txt: {e}")
        
        print(f"[INFO] {len(self.accounts)} Cookie Accounts loaded.")

    async def connect_current(self):
        if not self.accounts: return False
        acc = self.accounts[self.current_index]
        try:
            client = GeminiClient(secure_1psid=acc['1PSID'], secure_1psidts=acc['1PSIDTS'])
            await client.init(timeout=30, auto_close=False, auto_refresh=False)
            acc['client'] = client
            return True
        except: return False

    def get_client(self):
        if not self.accounts: return None
        return self.accounts[self.current_index].get('client')

    async def rotate(self):
        if not self.accounts: return
        self.current_index = (self.current_index + 1) % len(self.accounts)
        print(f"🔄 [COOKIE] Rotating to Account #{self.current_index + 1}")
        await self.connect_current()


# --- COOKIE ROTATION MANAGER ---
class RotationManager:
    """
    Cookie Rotation System:
    - Rotates account every 10 requests to avoid soft bans.
    - It is recommended to have at least 2 accounts logged in (Firefox/Chrome).
    """
    def __init__(self):
        self.cookie_manager = CookieSessionManager()
        self.request_count = 0 
        self.BATCH_SIZE = 10  # Peticiones antes de rotar cuenta
        self.total_requests = 0

    async def initialize(self):
        self.cookie_manager.load_all()
        await self.cookie_manager.connect_current()
        print(f"✅ [INIT] System initialized. Accounts detected: {len(self.cookie_manager.accounts)}")
        print(f"📋 [CONF] Rotation: Every {self.BATCH_SIZE} requests.")

    async def increment_counter(self):
        """Increment counter and rotate if necessary."""
        self.total_requests += 1
        self.request_count += 1
        
        # Check if we need to rotate account
        if self.request_count >= self.BATCH_SIZE:
             print(f"🔄 [ROTATION] Limit of {self.BATCH_SIZE} requests reached. Rotating account preventively.")
             await self.cookie_manager.rotate()
             self.request_count = 0
        
        print(f"📈 [STATS] Segment requests: {self.request_count}/{self.BATCH_SIZE} | Total: {self.total_requests}")


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
rotation_manager = RotationManager()

# --- STATE ---
# Only for Cookies, official API is stateless
THREAD_STATE: Dict[int, Dict[str, Any]] = {}

# --- MODELS ---
class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = "gemini-3.0-pro"
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

# --- CORE LOGIC ---
async def execute_query(full_prompt: str, model_id_request: str):
    
    # Total attempts before giving up
    max_retries = 3 
    
    for attempt in range(max_retries):
        
        try:
            response_text = ""
            
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
            target_model = "gemini-2.5-flash" if "flash" in model_id_request.lower() else "gemini-3.0-pro"
            
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

            # ÉXITO
            await rotation_manager.increment_counter()
            return clean_response(response_text)

        except Exception as e:
            err_str = str(e)
            print(f"❌ Error in COOKIE mode: {err_str}")
            
            # If Rate Limit (429) -> Rotate Cookie
            if "429" in err_str or "Invalid response" in err_str:
                print("⚠️ Cookie Rate Limit. Rotating account...")
                THREAD_STATE[rotation_manager.cookie_manager.current_index] = {}  # Clear chat
                await rotation_manager.cookie_manager.rotate()
            else:
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
        
    # Build final prompt
    prompt_parts = []
    
    # 1. System Prompt
    if system_instruction:
        prompt_parts.append(system_instruction)
        
    # 2. Context (Previous Japanese lines)
    if previous_user_lines:
        ctx_block = ["### Context prior to sentence:"]
        for i, line in enumerate(previous_user_lines):
            ctx_block.append(f"{i+1}. {line}")
        prompt_parts.append("\n".join(ctx_block))
    
    # 3. Current Message (Includes Luna's template + text)
    if current_msg:
        prompt_parts.append("\n### TEXT TO TRANSLATE (DO NOT RETURN COMMENTS OR EXPLANATIONS):")
        # Explicit format instruction to avoid comments and facilitate copying
        prompt_parts.append("IMPORTANT: Put THE TRANSLATION inside a ``` code block for easy copying. All text outside this block will be ignored.")
        prompt_parts.append(current_msg)
         
    final_prompt = "\n\n".join(prompt_parts)

    answer = await execute_query(final_prompt, request.model)
    
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
            {"id": "gemini-3.0-pro", "object": "model", "owned_by": "google"},
            {"id": "gemini-2.5-flash", "object": "model", "owned_by": "google"}
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, access_log=False)