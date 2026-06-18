# DAY 3 NOTES – CODE SENSE REQUEST FLOW

## Day 3 Goal

Understand the complete request flow of Code Sense.

The goal is NOT:

* Understanding every line of code
* Memorizing implementation details
* Learning every backend function

The goal IS:

* Understanding how a user action travels through the system
* Understanding how frontend talks to backend
* Understanding how backend talks to AI
* Understanding how results return to the UI

---

# Core Architecture

Every major feature in Code Sense follows the same architecture:

```text
Frontend Page
     ↓
API Layer (api.js)
     ↓
Backend Route (FastAPI)
     ↓
Service Layer
     ↓
AI / Search Layer
     ↓
Response
     ↓
Frontend UI
```

---

# Complete Code Sense Architecture

```text
User
 ↓
React Frontend
 ↓
Pages
 ↓
api.js
 ↓
FastAPI Routes
 ↓
Service Layer
 ↓
AI/Search Layer
 ↓
MongoDB
 ↓
FAISS
 ↓
OpenAI/Ollama/Anthropic
 ↓
Response
 ↓
React UI
```

---

# What Happens When a User Clicks a Button?

Example:

```text
Run Review
```

Flow:

```text
User
 ↓
React Component
 ↓
Click Handler
 ↓
API Call
 ↓
Backend Route
 ↓
Service
 ↓
LLM / Search Engine
 ↓
Response
 ↓
React State Update
 ↓
UI Re-render
```

---

# React Concepts Used Today

## Component

Example:

```jsx
function AIReview() {
}
```

Purpose:

```text
Reusable UI block
```

Examples:

```text
AIReview.jsx
ExplainCode.jsx
ImpactAnalysis.jsx
SemanticSearch.jsx
QAChat.jsx
Architecture.jsx
DependencyGraph.jsx
```

---

## State

Example:

```jsx
const [issues, setIssues] = useState([]);
```

Purpose:

```text
Store data that changes
```

Example:

Before review:

```js
issues = []
```

After review:

```js
issues = [
  {...},
  {...}
]
```

React automatically updates the UI.

---

## useEffect

Example:

```jsx
useEffect(() => {
}, []);
```

Purpose:

```text
Run code when component loads
```

In AIReview:

```text
Page loads
     ↓
Fetch repositories
     ↓
Populate dropdown
```

---

# Async / Await

## Why It Exists

API requests take time.

Example:

```text
Frontend
 ↓
Backend
 ↓
AI
 ↓
Response
```

May take:

```text
2 seconds
5 seconds
10 seconds
```

---

## Promise

Example:

```js
const data = fetch(...)
```

Immediately returns:

```js
Promise { <pending> }
```

Not actual data.

---

## async

Allows use of:

```js
await
```

Example:

```js
const handleRunReview = async () => {
}
```

---

## await

Example:

```js
const res = await reviewApi.analyze(...)
```

Meaning:

```text
Send request
 ↓
Wait for response
 ↓
Store response
 ↓
Continue execution
```

---

# API Layer

File:

```text
src/services/api.js
```

Purpose:

```text
Single place for all backend communication
```

Instead of:

```js
axios.post(...)
```

everywhere,

we use:

```js
reviewApi.analyze(...)
```

---

# Axios

Library used for HTTP requests.

Example:

```js
axios.post(...)
```

Used to communicate with backend.

---

# Base URL

Example:

```js
const BASE_URL = ...
```

Purpose:

```text
Backend address
```

Example:

```text
https://codesense-backend.onrender.com/api/v1
```

---

# Axios Instance

Example:

```js
const api = axios.create(...)
```

Purpose:

```text
Reusable axios configuration
```

Contains:

```text
Base URL
Timeout
Headers
```

---

# Request Interceptor

Example:

```js
api.interceptors.request.use(...)
```

Purpose:

```text
Runs before every request
```

Adds:

```http
Authorization: Bearer TOKEN
```

automatically.

---

# Response Interceptor

Purpose:

```text
Runs after every response
```

Handles:

```text
Token Expired
      ↓
Refresh Token
      ↓
Retry Request
```

---

# JWT Authentication

## Access Token

Stored in:

```js
localStorage
```

Sent with every request.

Example:

```http
Authorization: Bearer TOKEN
```

---

## Refresh Token

Used when:

```text
Access token expires
```

Flow:

```text
Request
 ↓
401 Unauthorized
 ↓
Refresh Token
 ↓
New Access Token
 ↓
Retry Request
```

---

# HTTP Methods

## GET

Purpose:

```text
Fetch data
```

Examples:

```js
api.get("/repositories")
api.get("/health")
```

Used for:

```text
List repositories
Get repository
Get architecture
Health check
```

---

## POST

Purpose:

```text
Send data to server
```

Examples:

```js
api.post("/review/analyze")
api.post("/explain")
api.post("/impact/analyze")
```

Used for:

```text
Run AI Review
Run Explain Code
Run Impact Analysis
Ask AI Questions
Upload Repository Information
```

---

## DELETE

Purpose:

```text
Remove data
```

Example:

```js
api.delete(...)
```

Used for:

```text
Delete repository
```

---

# AI REVIEW FLOW

## Purpose

Find:

```text
Security Issues
Performance Issues
Architecture Issues
Maintainability Issues
Bugs
```

---

## Request Payload

Frontend sends:

```json
{
  "repo_id": "123"
}
```

---

## Response

Backend returns:

```json
{
  "success": true,
  "repo_id": "123",
  "issues": [...]
}
```

---

## Full Flow

```text
User clicks Run Review
        ↓
AIReview.jsx
        ↓
handleRunReview()
        ↓
reviewApi.analyze()
        ↓
POST /review/analyze
        ↓
review.py
        ↓
ReviewService.run_review()
        ↓
MongoDB Repository Lookup
        ↓
Static Rule Engine
        ↓
Top 5 Files Selected
        ↓
_run_file_review()
        ↓
_run_llm_analysis()
        ↓
complete()
        ↓
llm_client.py
        ↓
OpenAI/Ollama/Anthropic
        ↓
JSON Issues Returned
        ↓
ReviewService
        ↓
review.py
        ↓
Frontend Response
        ↓
setIssues()
        ↓
Issue Cards Rendered
```

---

# Static Analysis

Traditional rule-based checking.

Examples:

```text
Hardcoded API Keys
eval()
pickle.loads()
Nested Loops
Large Files
Excessive Imports
```

No AI involved.

---

# Why Only Top 5 Files?

Suppose repository contains:

```text
500 files
```

Sending everything to GPT:

```text
Expensive
Slow
```

So Code Sense reviews:

```text
Largest 5 files
```

first.

---

# asyncio.gather()

Purpose:

Run multiple reviews simultaneously.

Instead of:

```text
File1
wait

File2
wait

File3
wait
```

Do:

```text
File1
File2
File3
File4
File5

parallel
```

Faster.

---

# LLM Client

Purpose:

Provide one interface for all AI providers.

Flow:

```text
Review Service
      ↓
complete()
      ↓
Provider
      ↓
OpenAI
or
Ollama
or
Anthropic
```

The rest of the application does not care which model is being used.

---

# EXPLAIN CODE FLOW

## Purpose

Explain selected code to developers.

---

## Request Payload

```json
{
  "repo_id": "123",
  "file_path": "src/App.jsx",
  "start_line": 10,
  "end_line": 40
}
```

---

## Full Flow

```text
ExplainCode.jsx
      ↓
handleExplain()
      ↓
explainApi.explain()
      ↓
POST /explain
      ↓
explain.py
      ↓
ExplainService
      ↓
Read Source Code
      ↓
RAG Context
      ↓
LLM
      ↓
Explanation Returned
      ↓
Frontend
      ↓
UI
```

---

# IMPACT ANALYSIS FLOW

## Purpose

Answer:

```text
If I modify this file,
what will break?
```

---

## Request Payload

```json
{
  "repo_id": "123",
  "file_path": "src/api.js",
  "symbol_name": "reviewApi",
  "algorithm": "bfs"
}
```

---

## Full Flow

```text
ImpactAnalysis.jsx
      ↓
impactApi.analyze()
      ↓
POST /impact/analyze
      ↓
impact.py
      ↓
ImpactService
      ↓
DependencyService
      ↓
Dependency Graph
      ↓
BFS / DFS Traversal
      ↓
Affected Files
      ↓
Risk Score
      ↓
Frontend
      ↓
UI
```

---

# What is BFS?

BFS = Breadth First Search

Purpose:

```text
Visit nearest dependencies first
```

Example:

```text
A
├─ B
├─ C
└─ D
```

Traversal:

```text
A
B
C
D
```

---

# What is DFS?

DFS = Depth First Search

Purpose:

```text
Go deep into dependency chain
```

Example:

```text
A
└─ B
   └─ C
      └─ D
```

Traversal:

```text
A
B
C
D
```

depth-first.

---

# SEMANTIC SEARCH FLOW

## Purpose

Search code by meaning.

Example:

```text
Where is JWT authentication implemented?
```

instead of exact keyword matching.

---

## Full Flow

```text
SemanticSearch.jsx
      ↓
searchApi.search()
      ↓
search.py
      ↓
SearchService
      ↓
Embeddings
      ↓
FAISS Vector Store
      ↓
Relevant Chunks
      ↓
Frontend
      ↓
UI
```

---

# What Are Embeddings?

Embeddings convert code/text into vectors.

Example:

```text
JWT Authentication
```

becomes:

```text
[0.23, -0.14, 0.81, ...]
```

Purpose:

```text
Meaning-based search
```

instead of keyword search.

---

# What is FAISS?

FAISS = Facebook AI Similarity Search

Purpose:

```text
Store embeddings
Find nearest vectors quickly
```

Used by:

```text
Semantic Search
Q&A Chat
RAG
```

---

# Q&A CHAT FLOW

## Purpose

Chat with repository.

Example:

```text
How does login work?
```

---

## Full Flow

```text
QAChat.jsx
      ↓
qaApi.ask()
      ↓
qa.py
      ↓
Retrieval Service
      ↓
Semantic Search
      ↓
Relevant Chunks
      ↓
LLM
      ↓
Answer
      ↓
Frontend
      ↓
UI
```

---

# RAG

RAG = Retrieval Augmented Generation

Purpose:

```text
Retrieve relevant code
Then send it to AI
```

Flow:

```text
Question
 ↓
Search repository
 ↓
Relevant code chunks
 ↓
LLM
 ↓
Answer
```

---

# DEPENDENCY GRAPH FLOW

## Purpose

Visualize file relationships.

---

## Full Flow

```text
DependencyGraph.jsx
      ↓
dependencyApi.buildGraph()
      ↓
dependency.py
      ↓
DependencyService
      ↓
Graph Builder
      ↓
Nodes + Edges
      ↓
Frontend Graph UI
```

---

# ARCHITECTURE SUMMARY FLOW

## Purpose

Generate high-level architecture understanding.

---

## Full Flow

```text
Architecture.jsx
      ↓
architectureApi.summarise()
      ↓
architecture.py
      ↓
ArchitectureService
      ↓
Repository Metadata
      ↓
LLM Summary
      ↓
Frontend
```

---

# REPOSITORY UPLOAD FLOW

## GitHub URL Upload

```text
Upload.jsx
      ↓
repositoriesApi.ingestGitHub()
      ↓
repositories.py
      ↓
github_loader.py
      ↓
repo_parser.py
      ↓
chunker.py
      ↓
embeddings
      ↓
FAISS
```

---

## ZIP Upload

```text
Upload.jsx
      ↓
uploadZip()
      ↓
repositories.py
      ↓
zip_loader.py
      ↓
repo_parser.py
      ↓
chunker.py
      ↓
embeddings
      ↓
FAISS
```

---

# Why Chunking Exists

Suppose a repository contains:

```text
50,000 lines
```

AI cannot process everything at once.

So repository is split into:

```text
Chunk 1
Chunk 2
Chunk 3
Chunk 4
...
```

Purpose:

```text
Efficient Search
Efficient RAG
Efficient AI Processing
```

---

# Day 3 Master Flow

```text
User Action
      ↓
React Page
      ↓
Click Handler
      ↓
api.js
      ↓
Axios
      ↓
FastAPI Route
      ↓
Service Layer
      ↓
Repository Data
      ↓
AI/Search Layer
      ↓
OpenAI/Ollama/Anthropic
      ↓
Response
      ↓
React State Update
      ↓
UI Re-render
```

---

# Final Interview Answer

Q. Explain Code Sense.

Answer:

Code Sense is an AI-powered repository intelligence platform.

Users upload repositories through GitHub URLs or ZIP files.

The backend parses the repository, extracts files and symbols, creates chunks, generates embeddings, and stores them in FAISS.

Features such as AI Review, Explain Code, Impact Analysis, Semantic Search, Q&A Chat, Architecture Summary, and Dependency Analysis operate on this indexed repository.

The frontend is built using React and communicates with a FastAPI backend.

Most features follow:

React Page
↓
API Layer
↓
FastAPI Route
↓
Service Layer
↓
AI/Search Layer
↓
Response
↓
UI

This architecture allows developers to understand, search, review, analyze, and interact with large repositories efficiently using AI.

What is JWT Authentication?

JWT = JSON Web Token

Purpose:

Verify user identity
without storing session data on server

Flow:

User Login
     ↓
Backend verifies user
     ↓
Access Token generated
     ↓
Stored in browser
     ↓
Sent with every request

Example:

Authorization: Bearer eyJhbGc...
Why Access Token?

Without token:

Backend doesn't know who is making request

With token:

Backend identifies user
Why Refresh Token?

Access tokens expire.

Flow:

Access Token Expired
       ↓
Refresh Token Used
       ↓
New Access Token Generated
       ↓
User stays logged in

Without refresh token:

User must login again
What is FastAPI?

Backend framework used in Code Sense.

Equivalent to:

React → Frontend
FastAPI → Backend

Example:

@router.post("/analyze")

Means:

When POST request arrives at /analyze
run this function
What is a Route?

Example:

@router.post("/analyze")

Route is:

Entry point into backend

Flow:

Frontend
     ↓
Route
     ↓
Service
What is a Service?

Example:

ReviewService
ExplainService
ImpactService

Purpose:

Business Logic Layer

Flow:

Route
     ↓
Service
     ↓
Actual Work
Why Separate Route and Service?

Bad:

Route contains 500 lines

Good:

Route
     ↓
Service

Benefits:

Clean Code
Easy Testing
Reusable Logic
What is Pydantic?

Example:

class ReviewRequest(BaseModel):
    repo_id: str

Purpose:

Validate incoming request data

Frontend sends:

{
   "repo_id":"123"
}

Pydantic verifies:

repo_id exists
repo_id is string
What is MongoDB Used For?

In Code Sense:

RepositoryDocument
ReviewReportDocument

Stored in MongoDB.

Purpose:

Store repositories
Store review reports
Store metadata

Flow:

Upload Repository
      ↓
MongoDB
      ↓
Review Uses Data
What is Dependency Injection?

Example:

service: ReviewService =
Depends(ReviewService)

FastAPI automatically creates:

ReviewService()

for you.

Benefit:

Cleaner Code
Loose Coupling
Easy Testing
What is LLM?

LLM = Large Language Model

Examples:

GPT
Claude
Llama
Mistral

In Code Sense:

OpenAI
Ollama
Anthropic

all act as LLM providers.

What is llm_client.py?

Purpose:

Single interface for all AI providers

Flow:

ReviewService
      ↓
complete()
      ↓
llm_client.py
      ↓
Provider

Benefit:

Switch provider without changing services
What is an API?

API = Application Programming Interface

Think:

Messenger between frontend and backend

Example:

Frontend says:
Run review

Backend says:
Here are 10 issues
What is Payload?

Payload = Data sent in request.

Example:

{
  "repo_id":"123"
}

Purpose:

Tell backend what operation to perform
What is Response?

Data returned by backend.

Example:

{
  "issues":[]
}

Purpose:

Provide result to frontend