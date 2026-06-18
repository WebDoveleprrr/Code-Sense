# 🚀 CodeSense

### AI-Powered Repository Intelligence Platform

CodeSense helps developers understand, search, analyze, and review large codebases using AI-powered semantic search, repository Q&A, architecture analysis, dependency mapping, impact analysis, and automated code review.

Instead of manually reading hundreds of files, developers can upload a repository and instantly explore its architecture, dependencies, authentication flow, business logic, and implementation details through natural language.

---

## ✨ Features

### 🔍 Semantic Search

Search repositories using intent instead of keywords.

Example:

```text
How is JWT authentication implemented?
```

CodeSense retrieves the most relevant files, functions, and code sections using vector similarity search.

---

### 💬 Repository Q&A

Chat with an entire codebase.

Example questions:

```text
How does authentication work?

Explain the repository structure.

Where is the database initialized?

What happens after login?
```

---

### ⚡ Explain Code

Generate detailed explanations for:

* Functions
* Classes
* Modules
* API Routes

Includes:

* Purpose
* Inputs
* Outputs
* Dependencies
* Complexity Analysis
* Suggested Improvements

---

### 🏗 Architecture Analysis

Automatically generates:

* System Overview
* Component Relationships
* Service Interactions
* Request Flow Explanations

---

### 🕸 Dependency Graph

Visualize:

* Module Dependencies
* Import Relationships
* Circular Dependencies
* Repository Structure

---

### 🎯 Impact Analysis

Predict the effect of code changes.

Example:

```text
What breaks if I modify auth.py?
```

CodeSense identifies:

* Affected Files
* Dependent Modules
* Potential Risk Areas

---

### 🤖 AI Code Review

Automatically evaluates:

* Code Quality
* Security Concerns
* Maintainability
* Performance Issues

Provides categorized recommendations.

---

## 🏛 System Architecture

```text
                    ┌───────────────┐
                    │ React Frontend│
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ FastAPI Backend│
                    └───────┬───────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼

 ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
 │ Repository  │    │ AI Services │    │ Auth Service│
 │ Ingestion   │    │             │    │             │
 └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
        │                  │                  │
        ▼                  ▼                  ▼

 ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
 │ FAISS       │    │ LLM Layer   │    │ JWT Auth    │
 │ Vector DB   │    │             │    │             │
 └─────────────┘    └─────────────┘    └─────────────┘

        │
        ▼

 ┌─────────────┐
 │ MongoDB     │
 └─────────────┘
```

---

## 🛠 Tech Stack

### Frontend

* React
* Vite
* Tailwind CSS
* React Router
* Axios

### Backend

* FastAPI
* Python
* Beanie ODM
* MongoDB Atlas

### AI & Search

* Sentence Transformers
* FAISS
* Hybrid Retrieval
* Cross-Encoder Re-ranking

### Authentication

* Google OAuth
* JWT Authentication

### Deployment

* Render
* MongoDB Atlas

---

## 📊 Platform Capabilities

| Capability            | Description                        |
| --------------------- | ---------------------------------- |
| Semantic Search       | Natural language repository search |
| Repository Q&A        | Chat with codebases                |
| Explain Code          | AI-generated code explanations     |
| Architecture Analysis | Automatic architecture discovery   |
| Dependency Graph      | Dependency visualization           |
| Impact Analysis       | Change impact prediction           |
| AI Review             | Automated code review              |

---

## 📁 Project Structure

```text
Code-Sense/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── ml/
│   │   ├── models/
│   │   ├── services/
│   │   └── vector_store/
│   │
│   └── tests/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   └── context/
│   │
│   └── public/
│
└── README.md
```

---

## 🚀 Local Setup

### Clone Repository

```bash
git clone https://github.com/WebDoveleprrr/Code-Sense.git
cd Code-Sense
```

---

### Backend Setup

```bash
cd backend

python -m venv venv

# Windows
venv\Scripts\activate

# Linux / Mac
source venv/bin/activate

pip install -r requirements.txt

uvicorn app.main:app --reload
```

Backend URL:

```text
http://localhost:8000
```

---

### Frontend Setup

```bash
cd frontend

npm install

npm run dev
```

Frontend URL:

```text
http://localhost:5173
```

---

## 🔧 Environment Variables

### Backend

```env
MONGO_URI=your_mongodb_connection_string

JWT_SECRET=your_secret_key

GOOGLE_CLIENT_ID=your_google_client_id

OPENAI_API_KEY=your_openai_api_key
```

### Frontend

```env
VITE_API_URL=http://localhost:8000/api/v1

VITE_GOOGLE_CLIENT_ID=your_google_client_id
```

---

## 🌐 API Endpoints

### Repository Management

| Method | Endpoint             | Description              |
| ------ | -------------------- | ------------------------ |
| POST   | /repositories/github | Ingest GitHub Repository |
| POST   | /repositories/upload | Upload ZIP Repository    |
| GET    | /repositories        | List Repositories        |
| GET    | /repositories/{id}   | Repository Details       |

### Search & AI

| Method | Endpoint           | Description          |
| ------ | ------------------ | -------------------- |
| POST   | /search            | Semantic Search      |
| POST   | /qa/ask            | Repository Q&A       |
| POST   | /explain           | Explain Code         |
| GET    | /dependency/{id}   | Dependency Graph     |
| GET    | /architecture/{id} | Architecture Summary |

---

## 📈 Future Improvements

* Multi-Repository Knowledge Graph
* Pull Request Intelligence
* Repository Comparison
* Code Ownership Analysis
* Team Collaboration Features
* Incremental Repository Indexing
* Advanced Architecture Diagrams

---

## 👨‍💻 Author

**Rohit Chowdary**

Computer Science Engineering Student

Built to explore how AI can dramatically improve codebase understanding, developer onboarding, and repository intelligence.

---

## ⭐ Why CodeSense?

CodeSense is not just another chatbot for source code.

It combines:

* Repository Ingestion Pipelines
* Semantic Vector Search
* Retrieval-Augmented Generation (RAG)
* Dependency Analysis
* Architecture Extraction
* Impact Prediction
* Automated Code Review

into a unified platform that helps developers understand complex software systems significantly faster.
