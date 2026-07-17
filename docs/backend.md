# CodeSense Backend Notes

# File Covered

* `backend/app/api/v1/repositories.py`

---

# What Is This File?

This file exposes all Repository Management APIs.

Its job is to allow the frontend to:

* Upload repositories
* Connect GitHub repositories
* View repositories
* View repository details
* View parsed files
* View chunks
* Check repository health
* Delete repositories

It acts as the API layer between the frontend and the ingestion system.

---

# Architecture Position

```text
Frontend
│
├── Dashboard.jsx
├── RepoSelector.jsx
├── SemanticSearch.jsx
└── Architecture.jsx
        │
        ▼
repositories.py
        │
        ▼
IngestionService
        │
        ├── GitHub Clone
        ├── ZIP Extraction
        ├── Parsing
        ├── Chunking
        ├── Embedding Generation
        ├── FAISS Index Creation
        └── MongoDB Storage
```

This file does NOT perform parsing, chunking, embedding, or indexing itself.

It only:

```text
Receive Request
↓
Validate Request
↓
Check Authentication
↓
Call Service Layer
↓
Return Response
```

---

# What Are HTTP Endpoints?

An endpoint is a URL exposed by the backend.

Example:

```python
@router.post("/github")
```

creates:

```text
POST /repositories/github
```

Frontend calls this endpoint to start repository ingestion.

Think of endpoints as doors into the backend.

Examples:

```text
POST   /repositories/github
POST   /repositories/upload
GET    /repositories
GET    /repositories/{repo_id}
GET    /repositories/{repo_id}/files
GET    /repositories/{repo_id}/chunks
GET    /repositories/{repo_id}/health
DELETE /repositories/{repo_id}
```

---

# Do GET and POST Come Under API Calls?

Yes.

All HTTP requests from frontend to backend are API calls.

Examples:

```javascript
axios.get("/repositories")
```

```javascript
axios.post("/repositories/upload")
```

Common methods:

```text
GET
POST
PUT
PATCH
DELETE
```

---

# What Is Repository Ingestion?

Ingestion means converting raw repository code into searchable indexed data.

Full ingestion flow:

```text
GitHub Repository / ZIP
↓
Clone / Extract
↓
Parse Files
↓
Chunk Code
↓
Generate Embeddings
↓
Build FAISS Index
↓
Store Metadata
↓
READY
```

Everything above is called Repository Ingestion.

---

# GitHub Repository Ingestion Flow

```text
User Pastes GitHub URL
↓
POST /repositories/github
↓
ingest_github_repo()
↓
create_github_repo_record()
↓
MongoDB Record Created
↓
Background Task Scheduled
↓
HTTP 202 Returned
↓
process_github_repo()
↓
Clone Repository
↓
Parse Files
↓
Chunk Files
↓
Generate Embeddings
↓
Build FAISS Index
↓
Update Status READY
```

---

# ZIP Upload Flow

```text
User Uploads ZIP
↓
POST /repositories/upload
↓
Validate Extension
↓
Create Repository Record
↓
Schedule Background Task
↓
Return Response
↓
Background Processing
↓
Extract ZIP
↓
Parse
↓
Chunk
↓
Embed
↓
Index
```

---

# What Are Parsed Files?

Parsing means understanding the structure of source code.

Example:

```python
def login():
    pass

class User:
    pass
```

Parser extracts:

```json
{
  "functions": 1,
  "classes": 1
}
```

Parsed files are files already analyzed by the parser.

Flow:

```text
Raw Source Code
↓
Parser
↓
Structure Extracted
↓
Metadata Generated
```

---

# What Are Chunks?

Chunks are smaller sections of source code created from large files.

Example:

```text
main.py (1000 lines)
```

becomes:

```text
Chunk 1 (1-200)
Chunk 2 (201-400)
Chunk 3 (401-600)
...
```

Chunking happens BEFORE embeddings.

Correct flow:

```text
Source Code
↓
Chunking
↓
Chunks
↓
Embedding Model
↓
Vector Embeddings
```

Important:

* Chunk = Actual code
* Embedding = Vector representation of code

Chunks are NOT smaller parts of embeddings.

Embeddings are generated FROM chunks.

---

# What Is Metadata?

Metadata means:

```text
Data about data
```

Example:

Actual code:

```python
def login():
    pass
```

Metadata:

```json
{
  "file":"auth.py",
  "functions":1,
  "classes":0,
  "imports":3
}
```

Examples of repository metadata:

* Total files
* Total functions
* Total classes
* Total imports
* Language breakdown
* File paths
* Token counts

Metadata describes code but is not the code itself.

---

# What Is Repository Listing?

Repository listing means returning all repositories owned by a user.

Endpoint:

```text
GET /repositories
```

Example response:

```json
[
  {
    "name":"CodeSense",
    "status":"READY"
  },
  {
    "name":"CampusBid",
    "status":"PROCESSING"
  }
]
```

Flow:

```text
Dashboard Opens
↓
GET /repositories
↓
Mongo Query
↓
Repository List Returned
```

---

# What Is Repository Health?

Health means:

```text
Is everything required for search still available and working?
```

Health endpoint checks:

```text
MongoDB Record Exists?
FAISS Index Exists?
Metadata File Exists?
```

Example:

```json
{
  "is_healthy": false,
  "issues": [
    "FAISS index missing"
  ]
}
```

---

# Difference Between Status and Health

## Status

Status shows where the repository is in the ingestion process.

Examples:

```text
PENDING
PROCESSING
READY
FAILED
```

Flow:

```text
Upload
↓
PENDING
↓
PROCESSING
↓
READY
```

---

## Health

Health shows whether repository resources currently exist and work.

Example:

```text
Status = READY
FAISS Deleted
Health = BAD
```

Status and Health can differ.

Example:

```text
Status = READY
Health = UNHEALTHY
```

because processing finished earlier but required files were later removed.

---

# Async vs Await vs BackgroundTasks

## async

Marks a function as asynchronous.

Example:

```python
async def search():
```

Meaning:

```text
Function can pause without blocking server.
```

---

## await

Used inside async functions.

Example:

```python
await RepositoryDocument.get(id)
```

Meaning:

```text
Pause here until result arrives.
Allow server to handle other requests meanwhile.
```

---

## BackgroundTasks

Runs work AFTER response is returned.

Example:

```python
background_tasks.add_task(
    service.process_repo
)
```

Flow:

```text
Request
↓
Response Returned Immediately
↓
Background Processing Starts
```

Used for long operations like repository ingestion.

---

# Comparison Table

| Feature              | async | await | BackgroundTasks |
| -------------------- | ----- | ----- | --------------- |
| Keyword              | Yes   | Yes   | No              |
| Used Inside Function | Yes   | Yes   | No              |
| Pauses Execution     | No    | Yes   | N/A             |
| Runs After Response  | No    | No    | Yes             |
| Used For DB Calls    | Yes   | Yes   | Sometimes       |
| Used For Long Jobs   | No    | No    | Yes             |

---

# What Does "Validation Moved To Background Task" Mean?

Old flow:

```text
Upload ZIP
↓
Validate ZIP
↓
Extract ZIP
↓
Return Response
```

Problem:

Large ZIP files make users wait.

New flow:

```text
Upload ZIP
↓
Store File
↓
Return Response
↓
Background Task Starts
↓
Validate ZIP
↓
Extract ZIP
```

Benefits:

```text
Faster Responses
Lower Blocking
Better User Experience
```

---

# What Is a Service Instance?

Class:

```python
class IngestionService:
```

Instance:

```python
service = IngestionService()
```

An instance is an object created from a class.

FastAPI creates service instances automatically using dependency injection.

Example:

```python
service: IngestionService = Depends(IngestionService)
```

FastAPI internally creates:

```python
service = IngestionService()
```

The route then uses:

```python
service.create_github_repo_record()
service.process_github_repo()
service.delete_repo()
```

---

# Dependency Injection

Example:

```python
service: IngestionService = Depends(IngestionService)
```

Purpose:

FastAPI automatically provides required objects.

Benefits:

* Cleaner code
* Easier testing
* Looser coupling
* Better maintainability

---

# Authentication Flow

```text
JWT Token
↓
get_current_user
↓
Decode Token
↓
Load UserDocument
↓
Inject current_user
↓
Route Executes
```

---

# Repository Security Check

Before accessing repository data:

```python
doc.user_id != current_user.id
```

Purpose:

Prevent users from accessing repositories belonging to other users.

---

# Pagination

Chunk endpoint supports:

```python
skip
limit
```

Equivalent SQL:

```sql
LIMIT 50 OFFSET 0
```

Purpose:

Avoid returning thousands of chunks at once.

---

# Why Use BackgroundTasks For Ingestion?

Repository ingestion can take minutes.

Without BackgroundTasks:

```text
User Waits
↓
Timeout Risk
↓
Poor UX
```

With BackgroundTasks:

```text
Immediate Response
↓
Processing Continues
```

---

# Interview One-Liners

### What is ingestion?

Transforming a raw repository into searchable indexed data through parsing, chunking, embedding generation, and FAISS indexing.

### What is metadata?

Descriptive information about repository contents such as file counts, functions, classes, imports, and language statistics.

### Difference between status and health?

Status indicates ingestion progress, while health indicates whether repository resources currently exist and function correctly.

### Why BackgroundTasks?

To allow long-running indexing operations to continue after the HTTP response has already been returned.

### What is a service instance?

An object created from a service class that contains business logic used by API routes.

### What is chunking?

Splitting large source files into smaller code segments before generating embeddings.

### What is parsing?

Analyzing source code structure and extracting information such as functions, classes, imports, and symbols.

# ==================================================

# PIPELINE / CHUNKING / VECTOR SEARCH CONCEPTS

# ==================================================

---

# FLOW VS PIPELINE

## Flow

Flow describes how execution moves through the system.

Think:

```text
Flow = Which files/components are involved
```

Example:

```text
Frontend
↓
repositories.py
↓
IngestionService
↓
pipeline.py
↓
faiss_store.py
```

Flow answers:

* What calls what?
* Which files participate?
* Where does execution go next?

---

## Pipeline

Pipeline describes how data changes as it moves through the system.

Think:

```text
Pipeline = How data is transformed
```

Example:

```text
Repository
↓
Parse
↓
Metadata
↓
Chunk
↓
Embed
↓
FAISS
↓
MongoDB
```

Pipeline answers:

* How is raw data transformed?
* What processing stages exist?

---

## Difference Between Flow and Pipeline

```text
Flow     = Where execution goes

Pipeline = How data changes
```

---

## Interview Answer

A flow describes the sequence of files or components involved in execution, while a pipeline describes the sequence of transformations applied to data.

---

# PIPELINE.PY

## What Is pipeline.py?

pipeline.py is the orchestrator of the repository ingestion process.

Think:

```text
Project Manager
```

It does NOT:

```text
Parse files
Chunk files
Generate embeddings
Store vectors
```

Instead it coordinates all of them.

---

## Architecture Position

```text
repositories.py
↓
IngestionService
↓
pipeline.py
↓
Parser
↓
Chunker
↓
Embedder
↓
FAISSStore
↓
MongoDB
```

---

## Why It Exists

Without a pipeline:

```text
One Huge Function
↓
Everything Mixed Together
```

With a pipeline:

```text
Parse
↓
Chunk
↓
Embed
↓
Index
```

Each component has one responsibility.

---

## Complete Ingestion Pipeline

```text
Repository Uploaded
↓
Acquire Source
↓
Parse Repository
↓
AST Parse
↓
Generate Metadata
↓
Chunk Files
↓
Generate Embeddings
↓
Store In FAISS
↓
Store In MongoDB
↓
Save Metadata
↓
READY
```

---

## Streaming Architecture

Old Approach:

```text
Load Entire Repository
↓
Chunk Entire Repository
↓
Embed Entire Repository
```

Problem:

```text
Huge Memory Usage
```

---

New Approach:

```text
Read File
↓
Chunk File
↓
Embed File
↓
Store File
↓
Next File
```

Benefit:

```text
Bounded Memory Usage
```

---

## Why Rank Files?

Large repositories may contain:

```text
5000+
Files
```

CodeSense may only index:

```text
Top 1000
```

Most important files get priority.

Examples:

```text
main.py
app.py
server.py
src/
services/
models/
```

Low priority:

```text
tests/
docs/
examples/
```

---

## Interview Question

Why rank files?

Answer:

Large repositories may exceed indexing limits. Ranking ensures important business logic files are indexed before less useful files such as tests and documentation.

---

# AST (ABSTRACT SYNTAX TREE)

## What Is AST?

AST stands for:

```text
Abstract Syntax Tree
```

Purpose:

Convert source code into structured information.

---

## Example

Code:

```python
def login(user):
    return True
```

AST:

```text
Function
│
├── Name = login
├── Parameter = user
└── Return = True
```

---

## Why Use AST?

AST allows CodeSense to extract:

```text
Functions
Classes
Interfaces
Structs
Imports
Symbols
```

Without AST:

```text
Raw Text
```

With AST:

```text
Structured Understanding
```

---

# CHUNKER.PY

## What Is chunker.py?

Purpose:

Convert parsed files into meaningful chunks before embedding.

Flow:

```text
Parsed Files
↓
chunker.py
↓
Chunks
↓
Embedder
```

---

## Why Chunking Exists

Embedding models cannot efficiently process:

```text
Entire Repository
Very Large Files
```

Instead:

```text
Large File
↓
Chunker
↓
Small Chunks
↓
Embedding Model
```

---

# Semantic Chunking

Preferred chunking strategy.

Example:

```python
def login():
    ...

def logout():
    ...
```

Produces:

```text
Chunk 1 = login()
Chunk 2 = logout()
```

Instead of:

```text
Lines 1-200
Lines 201-400
```

---

## Advantages

```text
Preserves Logic
Higher Recall
Better Retrieval Quality
Natural Code Boundaries
```

---

## Disadvantages

```text
Large Functions May Exceed Token Limits
May Require Sub-Chunking
```

---

## Semantic Chunking Tradeoff

Interview Question:

What are the tradeoffs of semantic chunking?

Answer:

Semantic chunking preserves logical units such as functions and classes, improving retrieval quality because embeddings represent complete functionality. However, very large functions may exceed embedding model limits and require additional sub-chunking.

---

# Window Chunking

Fallback strategy.

Used when:

```text
No Functions
No Classes
No Interfaces
No Structs
```

Examples:

```text
yaml
json
env
txt
config
```

---

## Example

```text
Lines 1-512
Lines 449-960
Lines 897-1408
```

---

## Why Window Chunking Exists

Some files have no meaningful AST structure.

Those files still need to be searchable.

---

# Chunk Overlap

Purpose:

Prevent context loss.

Without overlap:

```text
Chunk 1 = 1-100
Chunk 2 = 101-200
```

Important logic may be split.

---

With overlap:

```text
Chunk 1 = 1-100
Chunk 2 = 81-180
```

Context preserved.

---

## Interview Question

Why overlap chunks?

Answer:

Overlap ensures important context near chunk boundaries is preserved and remains searchable.

---

# Chunk Structure

Each chunk contains:

```text
file_path
language
content
start_line
end_line
chunk_index
token_count
chunk_type
symbol_name
metadata
```

This becomes the unit of retrieval.

---

# FAISS

## What Is FAISS?

FAISS stands for:

```text
Facebook AI Similarity Search
```

Purpose:

Fast vector similarity search.

---

## Why FAISS Exists

After chunking:

```text
Chunk
↓
Embedding
↓
Vector
```

We need a fast way to find:

```text
Most Similar Vectors
```

FAISS provides this.

---

# FAISS Flow

## Ingestion

```text
Chunk
↓
Embedding
↓
Vector
↓
FAISS
```

---

## Retrieval

```text
Query
↓
Embedding
↓
FAISS Search
↓
Top Matching Vectors
```

---

## What FAISS Stores

FAISS stores:

```text
Vectors
```

FAISS does NOT store:

```text
Code
File Paths
Chunk Metadata
Repository Metadata
```

---

# MetadataStore

## Why MetadataStore Exists

Problem:

FAISS returns:

```text
Vector #527
```

But does NOT know:

```text
Which File?
Which Chunk?
Which Lines?
```

---

MetadataStore provides:

```json
{
  "faiss_id": 527,
  "chunk_id": "abc123",
  "file_path": "auth.py",
  "start_line": 30,
  "end_line": 55
}
```

---

## Purpose

Maps:

```text
FAISS Vector
↓
Chunk
↓
File
↓
Lines
```

---

## Interview Question

Why MetadataStore?

Answer:

FAISS only stores vectors. MetadataStore maps vector IDs back to chunk information such as file path, line numbers, and MongoDB chunk IDs.

---

# Metadata Sidecar

## What Is A Sidecar?

A sidecar is an additional file stored beside another file.

Example:

```text
repo123/
│
├── index.faiss
└── index_meta.json
```

---

## Purpose

FAISS stores vectors.

Metadata sidecar stores:

```text
Embedding Dimension
Vector Count
Model Name
Creation Time
```

---

# FAISSStore

## What Is FAISSStore?

FAISSStore is the vector database layer of CodeSense.

Responsibilities:

```text
Store Embeddings
Search Embeddings
Save Indices
Load Indices
Delete Indices
Monitor Health
```

---

## Architecture Position

```text
pipeline.py
↓
Embedder
↓
FAISSStore
↓
Disk
```

During Retrieval:

```text
retrieval_service.py
↓
FAISSStore
↓
Vector Search
```

---

## File Layout

Each repository receives:

```text
VECTOR_STORE_DIR/repo_id/
│
├── index.faiss
└── index_meta.json
```

---

## Why Separate Index Per Repository?

Benefits:

```text
Isolation
Easier Deletion
Independent Search
Better Organization
```

---

# IndexFlatIP vs IndexFlatL2

## Interview Question

Why use IndexFlatIP instead of IndexFlatL2?

Answer:

Semantic search cares about meaning rather than physical distance. After normalization, Inner Product behaves like Cosine Similarity, which is the standard similarity metric for embeddings. IndexFlatIP therefore provides fast and effective semantic retrieval.

---

## Easy Version

```text
L2 Distance
=
How far apart vectors are

Cosine Similarity
=
How similar meanings are
```

CodeSense cares about:

```text
Meaning
```

Therefore:

```text
IndexFlatIP
```

is preferred.

---

# IVF Index

Small Repositories:

```text
IndexFlatIP
↓
Exact Search
↓
Highest Accuracy
```

---

Large Repositories:

```text
IndexIVFFlat
↓
Approximate Search
↓
Much Faster
```

Used when:

```text
More Than ~10,000 Vectors
```

---

# LRU Cache

## What Is LRU?

LRU:

```text
Least Recently Used
```

---

## Purpose

Keep frequently used FAISS indices in memory.

Without cache:

```text
Search
↓
Load Index From Disk
↓
Search
```

Repeated every request.

---

With cache:

```text
Search
↓
Memory Cache
↓
Immediate Access
```

Much faster.

---

## Interview Question

Why use an LRU cache?

Answer:

It reduces disk I/O and improves search latency by keeping frequently used FAISS indices in memory.

---

# Alternatives To FAISS

## Pinecone

Pros:

```text
Managed
Auto Scaling
Production Ready
```

Cons:

```text
Paid
Cloud Dependency
```

---

## Qdrant

Pros:

```text
Metadata Filtering
Open Source
Distributed
```

Cons:

```text
Additional Infrastructure
```

---

## ChromaDB

Pros:

```text
Easy Setup
RAG Friendly
```

Cons:

```text
Generally Slower Than Pure FAISS
```

---

## MongoDB Vector Search

Pros:

```text
Single Database
```

Cons:

```text
Usually Slower Than FAISS
Less Control Over Indexing
```

---

## Why FAISS For CodeSense?

Answer:

CodeSense runs as a self-hosted repository search system. FAISS provides fast local vector search, has no infrastructure cost, integrates easily with Python, and offers an excellent performance-to-complexity ratio for repository-scale semantic search.

---

# Master Ingestion Flow

```text
Repository
↓
repositories.py
↓
IngestionService
↓
pipeline.py
↓
Parser
↓
AST
↓
Chunker
↓
Embeddings
↓
FAISS
↓
MetadataStore
↓
MongoDB
↓
READY
```

---

# Master Retrieval Flow

```text
User Query
↓
Embedding Model
↓
Query Vector
↓
FAISS Search
↓
Vector IDs
↓
MetadataStore
↓
Chunk IDs
↓
MongoDB
↓
Chunk Content
↓
LLM
↓
Answer
```

---

# Revision One-Liners

### What is AST?

Structured representation of source code used to extract functions, classes, imports, and symbols.

### What is semantic chunking?

Function/class-based chunking that preserves code meaning.

### What is window chunking?

Fixed-size chunking used when no meaningful code structure exists.

### What is FAISS?

A vector similarity search engine used to retrieve relevant code chunks.

### Why MetadataStore?

To map FAISS vector IDs back to actual chunks and files.

### Why overlap chunks?

To preserve context near chunk boundaries.

### Why IndexFlatIP?

Because semantic search cares about meaning, and Inner Product behaves like Cosine Similarity on normalized vectors.

### Why FAISS over Pinecone/Qdrant?

Lower complexity, no cloud dependency, no cost, and excellent performance for repository-scale search.

# Backend Notes (Continuation)

---

# Abstract Syntax Tree (AST)

## What is an AST?

AST stands for **Abstract Syntax Tree**.

It is a tree representation of the structure of source code.

Instead of treating code as plain text, an AST represents programming constructs such as functions, classes, loops, and expressions as nodes in a tree.

Example:

```python
def add(a, b):
    return a + b
```

AST representation:

```
Module
│
└── FunctionDef(add)
      │
      ├── Arguments
      │      ├── a
      │      └── b
      │
      └── Return
             │
             +
            / \
           a   b
```

---

## Why use AST?

Without AST:

* Code is just text.
* Difficult to understand program structure.

With AST:

* Find functions
* Find classes
* Find decorators
* Find docstrings
* Find return types
* Understand nested code

---

## Advantages

* Grammar-aware
* Very accurate
* Ignores formatting
* Understands nesting
* Perfect for static analysis

---

## Disadvantages

* Language specific
* Python AST only understands Python
* Cannot parse C++, JavaScript, Java, etc.

---

## Interview Question

**Q:** Why use AST instead of Regex?

**Answer:**

AST understands the programming language grammar and correctly identifies language constructs such as functions, classes, decorators, and type annotations. Regex only matches text patterns and becomes unreliable for complex syntax.

---

# Parse Tree vs AST

Many people confuse these.

## Parse Tree

Represents every grammar rule.

Very detailed.

Contains punctuation and intermediate grammar nodes.

```
Grammar
↓

Parse Tree
```

---

## AST

Simplified representation.

Only keeps meaningful programming constructs.

```
Parse Tree
↓

Remove unnecessary grammar

↓

AST
```

---

## Comparison

| Parse Tree                 | AST                       |
| -------------------------- | ------------------------- |
| Grammar representation     | Semantic representation   |
| Very detailed              | Compact                   |
| Compiler parsing stage     | Static analysis / tooling |
| Contains all grammar nodes | Contains meaningful nodes |

---

# Tree-sitter

## What is Tree-sitter?

Tree-sitter is an incremental parser for programming languages.

It builds a parse tree from source code using language grammars.

---

## Why use Tree-sitter?

Instead of matching text,

Tree-sitter understands programming language syntax.

```
Source Code
↓

Grammar

↓

Parse Tree
↓

Extract Symbols
```

---

## Advantages

* Multi-language
* Grammar-aware
* Incremental parsing
* Very fast
* Excellent editor support

---

## Where is it used?

* Neovim
* Zed Editor
* Sourcegraph
* AI coding assistants
* Semantic search tools
* Code intelligence systems

---

## Alternatives

### Regex

Pros:

* Simple
* Lightweight

Cons:

* Doesn't understand grammar
* Breaks on complex syntax

---

### Compiler APIs

Examples:

* Clang
* Roslyn
* Java Compiler APIs

Pros:

* Extremely accurate

Cons:

* Heavy
* Language specific
* Harder integration

---

### Python AST

Pros:

* Built into Python
* Accurate

Cons:

* Python only

---

### Tree-sitter (Chosen)

Pros:

* Multi-language
* Lightweight
* Grammar-aware
* Production-ready

---

## Why not use Tree-sitter for Python?

Python already provides the built-in `ast` module.

Using it is simpler, officially maintained, and highly accurate.

---

# Repository Parser vs Language Parser

## Repository Parser

Works on the repository.

Responsibilities:

* Walk directories
* Skip ignored folders
* Detect languages
* Read files
* Handle encoding
* Detect binary files

Input:

```
Repository Folder
```

Output:

```
List of Source Files
```

It does **not** understand programming syntax.

---

## Language Parser

Works on one source file.

Responsibilities:

* Extract functions
* Extract classes
* Extract imports
* Extract comments
* Understand code structure

Input:

```
Source Code
```

Output:

```
Structured Metadata
```

---

## Comparison

| Repository Parser    | Language Parser      |
| -------------------- | -------------------- |
| Finds files          | Understands code     |
| Filesystem           | Programming language |
| Repository level     | File level           |
| Language independent | Language specific    |

---

## Easy Way to Remember

Repository Parser:

> "What files exist?"

Language Parser:

> "What is inside this file?"

---

# Parser Architecture in CodeSense

```
Repository
↓

repo_parser.py
↓

Language Detection
↓

Language Parser
      │
      ├── python_parser.py
      ├── cpp_parser.py
      ├── js_ts_parser.py
      └── tree_sitter_parser.py
↓

Metadata
↓

metadata_generator.py
↓

chunker.py
```

---

# Python Parser

Uses:

```
Python AST
```

Extracts:

* Functions
* Classes
* Imports
* Comments
* Docstrings
* Decorators
* Return types
* Arguments

---

## Why tokenize?

Python AST removes comments.

The tokenizer is used to recover comments so they can be included in metadata.

---

# C++ Parser

Current implementation:

```
Regex
↓

Metadata
```

Extracts:

* Functions
* Classes
* Structs
* Includes
* Namespaces
* Comments

---

## Why Regex?

Chosen because it:

* has no external dependency
* is lightweight
* is sufficient for common C++ syntax

---

## Limitations

* Doesn't understand grammar
* Complex templates are difficult
* Macros can confuse it
* False positives possible

---

# JavaScript / TypeScript Parser

Uses Regex.

Extracts:

* Functions
* Arrow Functions
* Classes
* Imports
* JSDoc
* Interfaces
* Type Aliases

---

## Why separate Arrow Functions?

Modern JavaScript and React frequently use:

```javascript
const login = () => {}
```

instead of

```javascript
function login(){}
```

Both need to be detected.

---

# Tree-sitter Parser

Purpose:

Provide a grammar-based parser for multiple languages.

Current project status:

The project already has:

* python_parser.py
* cpp_parser.py
* js_ts_parser.py

Tree-sitter appears to be an alternative or future parser implementation rather than the primary parser currently used.

---

## Likely Future Architecture

```
Repository
↓

repo_parser.py
↓

Language?

      Python
          ↓
      Python AST

      JS
          ↓
      Tree-sitter

      TS
          ↓
      Tree-sitter

      C++
          ↓
      Tree-sitter
```

---

# Grammar

Grammar defines the syntax rules of a programming language.

Tree-sitter loads a grammar for each supported language.

Examples:

* Python Grammar
* C++ Grammar
* JavaScript Grammar
* TypeScript Grammar

The parser follows these rules to build a parse tree.

---

# Parser Dispatch

Parser dispatch is selecting the correct parser based on file language.

Example:

```
.py
↓

python_parser.py

.cpp
↓

cpp_parser.py

.js
↓

js_ts_parser.py
```

---

# Doxygen

Doxygen is a documentation style used in C/C++.

Example:

```cpp
/**
 * Login function
 */
```

Unlike ordinary comments, Doxygen comments describe the following function or class.

The parser associates the documentation with that symbol.

---

# JSDoc

JavaScript equivalent of Doxygen.

Example:

```javascript
/**
 * Login function
 */
```

Used to document functions and classes.

---

# Interfaces

TypeScript only.

Example:

```typescript
interface User {
    id: number;
}
```

Defines a contract that classes or objects must follow.

JavaScript does not support interfaces.

---

# Type Aliases

TypeScript only.

Example:

```typescript
type UserID = string;
```

Creates an alias for another type.

---

# Namespace

C++ namespaces group related classes and functions.

Example:

```cpp
namespace auth {

}
```

Avoids naming conflicts.

---

# Parser Comparison

| Parser                | Technique            | Languages      |
| --------------------- | -------------------- | -------------- |
| repo_parser.py        | Filesystem traversal | All            |
| python_parser.py      | Python AST           | Python         |
| cpp_parser.py         | Regex                | C/C++          |
| js_ts_parser.py       | Regex                | JS / TS        |
| tree_sitter_parser.py | Tree-sitter          | Multi-language |

---

# Current Ingestion Pipeline

```
Repository
↓

repo_parser.py
↓

Language Parser
↓

metadata_generator.py
↓

chunker.py
↓

embedder.py
↓

FAISS

↓

MetadataStore

↓

MongoDB
```

---

# Important Interview Questions

## Q1 Why use AST instead of Regex?

AST understands grammar whereas Regex only matches text patterns.

---

## Q2 Why use Tree-sitter?

Tree-sitter provides accurate grammar-aware parsing across multiple programming languages while remaining lightweight and fast.

---

## Q3 Why keep separate language parsers?

Each language has unique syntax. Dedicated parsers extract language-specific information while returning a common metadata schema.

---

## Q4 Why is the metadata schema common?

So the remaining pipeline (chunker, embedder, FAISS, retrieval) becomes language independent.

---

## Q5 Why does CodeSense have tree_sitter_parser.py if other parsers already exist?

It appears to be a future or alternative grammar-based implementation that can eventually replace the regex-based parsers without changing the rest of the ingestion pipeline.

---

# Key Architecture Principle Learned

Every parser—whether AST-based, Regex-based, or Tree-sitter-based—produces the **same metadata format**.

Because of this standardization, downstream components never need to know how the metadata was extracted.

This is a classic example of **separation of concerns** and **interface-based design**.
