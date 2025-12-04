from fastapi import FastAPI, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .llm_agent import handle_chat_message
import traceback
import sys

app = FastAPI(title="LLM-driven Travel Agent (Corrected Backend)")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class ChatIn(BaseModel):
    message: str
    conversation: list = []

@app.post("/chat")
async def chat(body: ChatIn = Body(...)):
    try:
        resp = await handle_chat_message(body.message, body.conversation or [])
        return resp
    except Exception as e:
        print("ERROR in /chat:", e, file=sys.stderr)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "ok"}
