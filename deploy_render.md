Render deployment steps:
1. Push this repo to GitHub.
2. Backend: create a Web Service in Render, point to backend/app, use Dockerfile. Set env vars: OPENAI_API_KEY, OPENWEATHER_API_KEY (optional), LLM_MODEL, USE_LLM=true.
3. Frontend: create a Static Site or Web Service. Build: npm install && npm run build. Publish dir: dist. Set VITE_BACKEND_URL to backend URL.
