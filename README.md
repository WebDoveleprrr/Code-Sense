# CodeSense Frontend

React + Tailwind frontend for the CodeSense AI-powered repository intelligence platform.

## Quick Start

```bash
cd frontend
npm install
cp .env.example .env         # set REACT_APP_API_URL
npm start                    # runs on http://localhost:3000
```

## Build for Production

```bash
npm run build
# Output: build/ — deploy to Vercel or static host
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `REACT_APP_API_URL` | `http://localhost:8000/api/v1` | Backend API base URL |

## Pages

| Route | Page | Description |
|---|---|---|
| `/` | Dashboard | Stats, quick actions, repo list |
| `/upload` | Upload | GitHub URL or ZIP ingestion |
| `/search` | SemanticSearch | FAISS-backed code search |
| `/qa` | QAChat | RAG-powered Q&A chat |
| `/explain` | ExplainCode | AI explanation of code ranges |
| `/graph` | DependencyGraph | D3 import/dependency visualization |
| `/architecture` | Architecture | AI architecture summary |

## API Compatibility

All API calls target `/api/v1/*` as defined in `backend/app/api/router.py`:

- `POST /repositories/github` — GitHub ingestion
- `POST /repositories/upload` — ZIP ingestion
- `GET  /repositories` — list repos
- `GET  /repositories/{id}` — repo detail
- `POST /search` — semantic search
- `POST /qa/ask` — Q&A
- `POST /explain` — code explanation
- `GET  /dependency/{id}` — dependency graph
- `GET  /architecture/{id}` — architecture summary
