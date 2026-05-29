# Architecture & Repository Structure

CodeSense is an AI-powered repository semantic search and codebase explanation platform.

## Repository Layout

```
project-root/
│
├── backend/                  # FastAPI Backend application
│   ├── app/                  # FastAPI main source folder
│   │   ├── api/              # Route endpoints (v1)
│   │   ├── core/             # Configuration, exceptions, middlewares
│   │   ├── db/               # Database drivers (MongoDB client setup)
│   │   ├── ml/               # Embedder, parse engines, langchain/RAG components
│   │   ├── models/           # ODM/ODM schemas (MongoDB models)
│   │   ├── schemas/          # Pydantic validation schemas
│   │   ├── services/         # Application business logic services
│   │   ├── utils/            # Helper functions
│   │   └── vector_store/     # FAISS vector store database integration
│   │
│   ├── tests/                # Migrated python tests
│   │   ├── test_embeddings_and_vector_store.py
│   │   ├── test_health.py
│   │   ├── test_parsing_pipeline.py
│   │   ├── test_rag_pipeline.py
│   │   └── test_requests.py
│   │
│   ├── app_logger.py         # Application logging wrapper
│   ├── requirements.txt      # Python backend packages dependency list
│   └── run.py                # Development server execution script
│
├── frontend/                 # React Frontend application
│   ├── src/                  # React views, components, services, and hooks
│   ├── public/               # Static assets
│   ├── package.json          # Node dependency configuration
│   └── vite.config.js        # Vite build tool configuration
│
├── docs/                     # System documentation folder
│   ├── architecture.md
│   ├── embeddings_and_vector_search.md
│   └── semantic_search_rag.md
│
├── .env.example              # Template for environment settings
├── docker-compose.yml        # Multi-container local deployment spec
├── README.md                 # Entry documentation
└── .gitignore                # Version control exclusions
```

## Key Technologies
- **Backend**: FastAPI, Pytest, Loguru, Uvicorn, LangChain, FAISS, PyMongo
- **Frontend**: React, Vite, Tailwind CSS
- **Database**: MongoDB (running via Docker)
- **Deployment**: Docker, Docker Compose
