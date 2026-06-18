# Code Sense Mastery Plan — Day 1 Notes

## Goal: Understand the Overall Architecture of Code Sense

---
# 1. What is Code Sense?

Code Sense is an AI-powered Repository Intelligence Platform.

It helps users:

* Upload repositories
* Perform semantic search
* Ask questions about codebases
* Generate code explanations
* Analyze architecture
* Generate dependency graphs
* Perform impact analysis
* Run AI code reviews
---

# 2. High-Level Architecture

```text
User
 ↓
React Frontend
 ↓
API Layer (api.js)
 ↓
FastAPI Backend
 ↓
Routes
 ↓
Services
 ↓
Parser
 ↓
Embeddings
 ↓
FAISS Vector Store
 ↓
RAG Pipeline
 ↓
LLM
 ↓
Response
 ↓
Frontend
```

---

# 3. Project Structure

## Frontend

```text
frontend/
 ├── src/
 │    ├── pages/
 │    ├── components/
 │    ├── hooks/
 │    ├── services/
 │    └── utils/
```

## Backend

```text
backend/
 ├── app/
 │    ├── api/
 │    ├── services/
 │    ├── ml/
 │    ├── db/
 │    ├── models/
 │    ├── schemas/
 │    ├── core/
 │    ├── utils/
 │    └── vector_store/
```

---

# 4. Frontend Components

## Pages

```text
AIReview.jsx
Architecture.jsx
Dashboard.jsx
DependencyGraph.jsx
ExplainCode.jsx
ImpactAnalysis.jsx
Login.jsx
QAChat.jsx
SemanticSearch.jsx
Upload.jsx
```

Purpose:

* Display UI
* Accept user input
* Show AI results

---

## Components

```text
AppShell.jsx
Sidebar.jsx
CodeBlock.jsx
RepoSelector.jsx
```

Purpose:

* Reusable UI elements

---

## Hooks

```text
useAuth.js
useQA.js
useRepositories.js
useSearch.js
```

Purpose:

* State management
* API interaction logic

---

## Services

```text
api.js
```

Purpose:

* Connect frontend with backend APIs

---

## Utils

```text
helpers.js
```

Purpose:

* Shared helper functions

---

# 5. Backend Components

## Routes

Located in:

```text
backend/app/api/v1
```

Files:

```text
architecture.py
dependency.py
explain.py
health.py
impact.py
qa.py
repositories.py
review.py
search.py
vector_store.py
```

Purpose:

* Receive API requests
* Decide which service should handle them

Think:

```text
Route = Reception Desk
```

---

## Services

Located in:

```text
backend/app/services
```

Files:

```text
architecture_service.py
dependency_service.py
explain_service.py
impact_service.py
ingestion_service.py
other_services.py
qa_service.py
retrieval_service.py
review_service.py
search_service.py
```

Purpose:

* Business logic
* AI workflow execution

Think:

```text
Service = Engineer doing the work
```

---

## Database Layer

```text
app/db
app/models
```

Purpose:

* Store metadata
* Store repository information

---

## Vector Store Layer

```text
app/vector_store
```

Purpose:

* Store embeddings
* Perform similarity search

Technology:

```text
FAISS
```

---

## ML Layer

```text
app/ml
```

Purpose:

* Embeddings
* Parsing
* Retrieval
* RAG pipeline

---

# 6. Technology Stack

## React

Purpose:

* Frontend UI

Alternative:

* Angular
* Vue

Without React:

```text
No user interface
```

---

## Vite

Purpose:

* Build and run frontend

Alternative:

* Webpack
* Parcel

Without Vite:

```text
Frontend cannot run/build properly
```

---

## FastAPI

Purpose:

* Backend framework
* API creation

Alternative:

* Flask
* Django

Without FastAPI:

```text
No backend APIs
```

---

## MongoDB

Purpose:

* Persistent storage

Alternative:

* PostgreSQL
* MySQL

Without MongoDB:

```text
No data persistence
```

---

## FAISS

Purpose:

* Vector similarity search

Alternative:

* Pinecone
* Weaviate
* Qdrant

Without FAISS:

```text
Semantic search breaks
```

---

## LangChain

Purpose:

* AI workflow orchestration

Alternative:

* LlamaIndex
* Haystack

Without LangChain:

```text
Need custom RAG implementation
```

---

## Embedding Model

Purpose:

* Convert chunks into vectors

Without Embeddings:

```text
No semantic search
```

---

## LLM

Examples:

```text
GPT
Gemini
Claude
Llama
```

Purpose:

* Generate answers
* Generate explanations
* Generate reviews

Without LLM:

```text
No AI output
```

---

## Docker

Purpose:

* Consistent deployment

Without Docker:

```text
Environment issues increase
```

---

## Docker Compose

Purpose:

* Run multiple services together

Without Docker Compose:

```text
Need manual startup
```

---

# 7. What is an API?

API = Application Programming Interface

Purpose:

```text
Frontend
    ⇄
Backend
```

Think:

```text
API = Waiter
```

Example:

```text
POST /explain
POST /search
POST /qa
```

APIs allow frontend pages to communicate with backend logic.

---

# 8. What is FastAPI?

FastAPI is a Python framework used to build backend APIs.

Purpose:

```text
Receive requests
Run backend logic
Return responses
```

Think:

```text
React = Frontend Framework

FastAPI = Backend Framework
```

---

# 9. What is a Route?

A Route connects:

```text
URL
 ↓
Python Function
```

Example:

```python
@router.post("/search")
```

Meaning:

```text
When /search is called,
run this function.
```

Think:

```text
Route = Reception Desk
```

It receives requests and forwards them to services.

---

# 10. What is a Service?

A service contains actual business logic.

Example:

```text
search_service.py
qa_service.py
review_service.py
```

Think:

```text
Route = Receives work

Service = Performs work
```

---

# 11. What is a Parser?

Parser reads a repository and converts it into a structured format.

Flow:

```text
Repository
 ↓
Parser
 ↓
Chunks
```

Parser responsibilities:

* Read files
* Read folders
* Extract code
* Prepare data for AI

Think:

```text
Parser = Repository Reader
```

---

# 12. What is a Chunk?

A chunk is a small piece of code or text extracted from a repository.

Example:

```python
def login():
    pass
```

This can become a chunk.

Properties:

```text
Human-readable
Contains actual code
Created by parser
```

Think:

```text
Chunk = Small section of repository
```

---

# 13. What is an Embedding?

An embedding converts a chunk into numbers.

Example:

```text
Chunk:
def login()

↓

Vector:
[0.81, 0.22, 0.67, ...]
```

Purpose:

```text
Represent meaning mathematically
```

---

# 14. What is a Vector?

A vector is the numerical representation of meaning.

Example:

```text
[0.81, 0.22, 0.67, ...]
```

Properties:

```text
Machine-readable
Created from embeddings
Used by FAISS
```

Think:

```text
Vector = Mathematical meaning of a chunk
```

---

# 15. Chunk vs Vector

| Chunk             | Vector                     |
| ----------------- | -------------------------- |
| Actual code/text  | Numbers                    |
| Human-readable    | Machine-readable           |
| Created by parser | Created by embedding model |
| Sent to LLM       | Used for similarity search |

---

# 16. Why Do We Need Embeddings?

Parser only creates chunks.

Example:

```text
login()
jwt_authenticate()
verify_token()
```

User asks:

```text
How does authentication work?
```

The word:

```text
authentication
```

may not exist in code.

Embeddings allow semantic understanding.

Result:

```text
authentication
≈
login
≈
jwt_authenticate
≈
verify_token
```

---

# 17. What is FAISS?

FAISS is a vector search engine.

Purpose:

```text
Store vectors
Find similar vectors
```

Think:

```text
FAISS = Google Search for embeddings
```

---

# 18. What is Semantic Search?

Normal Search:

```text
Exact keyword match
```

Semantic Search:

```text
Meaning-based search
```

Example:

```text
authentication
```

can find:

```text
login
jwt_authenticate
verify_token
```

even if authentication never appears.

---

# 19. What is RAG?

RAG = Retrieval Augmented Generation

Flow:

```text
Question
 ↓
Retrieve Relevant Chunks
 ↓
Send To LLM
 ↓
Generate Answer
```

Purpose:

```text
Allow LLM to answer using repository code
instead of guessing.
```

---

# 20. Complete Internal Flow of Code Sense

```text
Repository
 ↓
Parser
 ↓
Chunks
 ↓
Embedding Model
 ↓
Vectors
 ↓
FAISS
 ↓
User Question
 ↓
Question Embedding
 ↓
Vector Similarity Search
 ↓
Relevant Chunks
 ↓
LLM
 ↓
Generated Answer
 ↓
Frontend Display
```

---

# 21. Frontend ↔ Backend Mapping

| Frontend Page       | Backend Route   | Service                 |
| ------------------- | --------------- | ----------------------- |
| Login.jsx           | Auth APIs       | Auth Service            |
| Dashboard.jsx       | repositories.py | Repository Services     |
| Upload.jsx          | repositories.py | ingestion_service.py    |
| ExplainCode.jsx     | explain.py      | explain_service.py      |
| SemanticSearch.jsx  | search.py       | search_service.py       |
| QAChat.jsx          | qa.py           | qa_service.py           |
| Architecture.jsx    | architecture.py | architecture_service.py |
| DependencyGraph.jsx | dependency.py   | dependency_service.py   |
| ImpactAnalysis.jsx  | impact.py       | impact_service.py       |
| AIReview.jsx        | review.py       | review_service.py       |

---

# 22. How Explain Code Works

```text
ExplainCode.jsx
 ↓
api.js
 ↓
POST /explain
 ↓
explain.py
 ↓
explain_service.py
 ↓
retrieval_service.py
 ↓
LLM
 ↓
Response
 ↓
Frontend
```

---

# Day 1 Final Understanding

Code Sense works as:

```text
User
 ↓
React Frontend
 ↓
FastAPI Backend
 ↓
Routes
 ↓
Services
 ↓
Parser
 ↓
Chunks
 ↓
Embeddings
 ↓
Vectors
 ↓
FAISS Search
 ↓
Relevant Chunks
 ↓
LLM
 ↓
Answer
 ↓
Frontend
```

Core Idea:

```text
Parser = Repository Reader

Chunk = Piece of Code

Embedding = Meaning Converter

Vector = Numerical Meaning

FAISS = Similarity Search Engine

RAG = Retrieve + Generate

LLM = AI Software Engineer
```
1. Route does not open a page.
   Frontend page calls the route.

2. Parser creates chunks.
   Embeddings create vectors.

3. FAISS searches vectors.
   LLM reads chunks.

4. Vectors are used for retrieval.
   They are not used to execute code.

5. FastAPI is the backend framework.
   React is the frontend framework.

6. API is the communication layer between frontend and backend.

7. Service layer performs actual work.
   Route layer only receives and forwards requests.

   Common Misconceptions Cleared

1. Route does not open a page.
   Frontend page calls the route.

2. Parser creates chunks.
   Embedding model creates vectors.

3. FAISS stores/searches vectors.
   LLM reads original chunks.

4. Vectors are used for retrieval.
   They are not used for code execution.

5. Semantic search retrieves relevant code.
   It does not execute code.

6. FastAPI is the backend framework.
   React is the frontend framework.

7. API is not a separate server.
   API endpoints are part of the backend.

8. Service layer performs work.
   Route layer receives and forwards requests.

9. Ollama is a model runner.
   LangChain is a workflow/orchestration framework.

10. Retrieval and execution are different systems.