LLM-driven Travel Agent - Production ZIP
Folders:
- backend/app : FastAPI backend (Dockerfile included). Put CSVs in backend/app/data/ (already included).
- frontend     : React Vite frontend. Set VITE_BACKEND_URL env var when deploying.

Environment variables (backend):
- OPENAI_API_KEY (required)
- OPENWEATHER_API_KEY (optional for live weather)
- LLM_MODEL (gpt-4o or gpt-4o-mini)
