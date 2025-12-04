\
    from fastapi import FastAPI, Body, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    from .llm_agent import handle_chat_message

    app = FastAPI(title="LLM-driven Travel Agent (Production)")
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
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/health")
    def health():
        return {"status": "ok"}
