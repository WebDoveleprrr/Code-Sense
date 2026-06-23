# CodeSense Frontend Notes (Interview-Oriented)

# 1. Overall Frontend Architecture

```text
main.jsx
    ↓
App.jsx
    ↓
AuthProvider
    ↓
BrowserRouter
    ↓
ProtectedRoute
    ↓
AppShell
    ↓
Pages
```

### Interview Answer

**What is the role of main.jsx?**

```text
main.jsx is the frontend entry point.
It mounts the React application into the browser DOM and wraps the application with global providers such as GoogleOAuthProvider.
```

---

**What is the role of App.jsx?**

```text
App.jsx acts as the frontend orchestrator.

Responsibilities:
1. Configure routes.
2. Protect authenticated pages.
3. Initialize global providers.
4. Connect all pages together.
```

---

# 2. Routing Concepts

## Route vs Navigate

### Route

```text
Defines a path.
```

Example:

```jsx
<Route path="/dashboard" element={<Dashboard />} />
```

---

### Navigate

```text
Moves the user to a path.
```

Example:

```jsx
navigate("/dashboard")
```

---

### Easy Analogy

```text
Route = Road

Navigate = Vehicle using the road
```

---

### Flow

```text
User Click
    ↓
navigate("/dashboard")
    ↓
React Router finds matching Route
    ↓
Dashboard Page Opens
```

---

# 3. Authentication Architecture

## Complete Login Flow

```text
User
    ↓
Google Login
    ↓
Google returns ID Token
    ↓
Frontend sends token
    ↓
POST /auth/google
    ↓
Backend verifies Google token
    ↓
Creates JWT tokens
    ↓
Returns access token
    ↓
Returns refresh token
    ↓
AuthContext.login()
    ↓
Stored in localStorage
    ↓
User authenticated
```

---

## JWT Analogy

```text
Movie Ticket System
```

### Backend

```text
Booking Counter
```

Creates:

```text
JWT Access Token
```

---

### Frontend

Stores:

```text
Access Token
Refresh Token
```

---

### Protected API

```text
Frontend sends JWT
    ↓
Backend validates JWT
    ↓
Access Granted
```

---

# 4. Access Token vs Refresh Token

## Access Token

```text
Short-lived ticket.
```

Example:

```text
Valid for 60 minutes.
```

Used for:

```text
Search
Upload
QA
Architecture
Review
```

---

## Refresh Token

```text
Long-lived backup ticket.
```

Used to create:

```text
New Access Token
```

without asking the user to login again.

---

## Token Refresh Flow

```text
User uses app
    ↓
Access token expires
    ↓
Backend returns 401
    ↓
Axios Interceptor catches 401
    ↓
restoreSession()
    ↓
POST /auth/refresh
    ↓
New access token generated
    ↓
Original request retried
    ↓
User sees no interruption
```

---

## Interview Answer

```text
Access tokens are short-lived credentials attached to every protected request.

Refresh tokens are used to silently generate new access tokens without requiring the user to log in again.
```

---

# 5. Why AuthContext Exists

Problem:

```text
Navbar needs user
Dashboard needs user
Profile needs user
Settings needs user
```

Passing through props:

```text
App
 ↓
Layout
 ↓
Navbar
 ↓
Profile
```

becomes messy.

---

Solution:

```text
AuthContext
```

---

Flow:

```text
AuthProvider
    ↓
Stores auth state
    ↓
Any component
    ↓
useContext(AuthContext)
    ↓
Access auth state
```

---

### Interview Answer

```text
AuthContext prevents prop drilling and provides a single global source of truth for authentication state.
```

---

# 6. Why AuthContext Exposes Window Functions

Problem:

```text
api.js is outside React
```

Therefore:

```text
Cannot use hooks
Cannot use useContext
```

---

Solution:

```text
window.__codesenseRestoreSession
window.__codesenseLogout
```

---

Flow

```text
Axios Interceptor
    ↓
401 Error
    ↓
window.__codesenseRestoreSession()
    ↓
AuthContext
    ↓
React state updated
```

---

### Interview Answer

```text
The Axios interceptor exists outside the React component tree, so React hooks cannot be used there. Exposing restoreSession on window allows the interceptor to trigger React authentication logic safely.
```

---

# 7. API Fundamentals

## What is an API?

```text
Bridge between frontend and backend.
```

---

Flow

```text
Frontend
    ↓
API
    ↓
Backend
```

---

Example

```text
Frontend asks:
"Search authentication code"

Backend performs:
Semantic Search

Backend returns:
Results
```

---

## What is an Endpoint?

Example:

```text
POST /search
POST /qa
POST /repositories
GET /repositories
```

Each one:

```text
Endpoint
```

---

### Difference

```text
API = Entire communication system

Endpoint = One specific URL inside API
```

---

# 8. Axios Architecture

## Why Axios?

Axios is an HTTP client.

Used to perform:

```text
GET
POST
PUT
DELETE
```

requests.

---

Alternatives:

```text
Fetch API
SuperAgent
Ky
jQuery AJAX
```

---

Why Axios?

```text
Interceptors
Automatic JSON handling
Timeout support
Cleaner syntax
```

---

# 9. Request Lifecycle

```text
Button Click
    ↓
Axios Request
    ↓
Request Interceptor
    ↓
Attach JWT
    ↓
Backend
    ↓
Response
    ↓
Response Interceptor
    ↓
UI Update
```

---

# 10. Request Interceptor

Purpose:

```text
Attach JWT automatically.
```

---

Flow

```text
User clicks Search
    ↓
Axios Request
    ↓
Read access_token
    ↓
Add Authorization Header
    ↓
Send Request
```

---

### Interview Answer

```text
Request interceptors centralize authentication logic by automatically attaching JWT tokens to outgoing requests.
```

---

# 11. Response Interceptor

Purpose:

```text
Handle token expiry.
```

---

Flow

```text
Request
    ↓
401 Unauthorized
    ↓
Interceptor catches error
    ↓
Refresh Token Flow
    ↓
Retry Original Request
```

---

# 12. useRepositories Hook

Purpose:

```text
Repository State Management
```

Maintains:

```text
repos
loading
error
```

---

Flow

```text
Page Loads
    ↓
fetchRepos()
    ↓
GET /repositories
    ↓
Store repositories
    ↓
UI updates
```

---

## Polling Flow

```text
Repository Upload
    ↓
Status = chunking
    ↓
Polling every 10s
    ↓
GET /repositories
    ↓
Status updated
    ↓
Ready
    ↓
Polling stops
```

---

# 13. useSearch Hook

Purpose:

```text
Manage semantic search state.
```

---

Flow

```text
Search Button
    ↓
search()
    ↓
POST /search
    ↓
Results returned
    ↓
Store results
    ↓
SemanticSearch.jsx updates
```

---

# 14. Semantic Search Flow

```text
User Query
    ↓
SemanticSearch.jsx
    ↓
useSearch()
    ↓
POST /search
    ↓
Backend
    ↓
Embeddings
    ↓
FAISS Search
    ↓
Top Results
    ↓
Frontend Result Cards
```

---

### Interview Answer

```text
Unlike keyword search, semantic search converts queries and code chunks into embeddings and retrieves results using vector similarity.
```

---

# 15. RepoSelector Flow

```text
Dropdown Open
    ↓
useRepositories()
    ↓
Repository List
    ↓
Filter Ready Repositories
    ↓
Select Repository
    ↓
repoId updated
```

---

# 16. CodeBlock Flow

```text
Code Received
    ↓
SyntaxHighlighter
    ↓
Line Numbers
    ↓
Copy Button
    ↓
Display Highlighted Code
```

---

# 17. QA Chat Flow

```text
User Question
    ↓
useQA.ask()
    ↓
POST /qa
    ↓
Backend RAG
    ↓
Gemini
    ↓
Answer Returned
    ↓
Assistant Message Added
```

---

# 18. Dashboard Flow

```text
Dashboard Opens
    ↓
GET /repositories
    ↓
Display Repository Cards
```

---

## Demo Repository Flow

```text
Explore Demo
    ↓
FastAPI Repo Exists?
        ↓
      Yes
        ↓
Navigate Search

OR

No
 ↓
GitHub Ingestion
 ↓
Refresh Dashboard
```

---

# 19. Protected Route Flow

```text
User Opens Dashboard
    ↓
ProtectedRoute
    ↓
authenticated?
       ↓
      Yes
       ↓
Render Page

      No
       ↓
Navigate Login
```

---

# 20. Frontend Security Flow

```text
Dashboard
    ↓
Backend says 401
    ↓
Redirect Login
```

---

Real Security:

```text
Frontend Check
    ↓
Backend JWT Validation
    ↓
Access Granted
```

---

### Interview Answer

```text
Frontend authentication improves user experience, but backend authentication is the true security layer because frontend code can always be bypassed.
```

---

# 21. Important React Hooks

## useState

Stores state.

```text
value changes
    ↓
Component rerenders
```

---

## useEffect

Runs side effects.

Example:

```text
API call
Event listener
Polling
```

---

## useContext

Access shared state.

Example:

```text
AuthContext
```

---

## useRef

Stores mutable value without rerender.

Example:

```text
Input focus
DOM reference
```

---

## useCallback

Purpose:

```text
Reuse function reference.
```

Not:

```text
Reuse function execution.
```

---

### Correct Interview Answer

```text
useCallback memoizes a function reference and prevents unnecessary recreations during rerenders.
```

---

# 22. Frontend Interview Questions

## Q1

Why use AuthContext?

Answer:

```text
To avoid prop drilling and maintain global authentication state.
```

---

## Q2

Why use Axios instead of Fetch?

Answer:

```text
Axios provides interceptors, automatic JSON parsing, timeout support, and cleaner request handling.
```

---

## Q3

What happens when JWT expires?

Answer:

```text
A 401 response triggers the Axios interceptor, which calls restoreSession() and obtains a new access token using the refresh token.
```

---

## Q4

Why use useCallback?

Answer:

```text
To memoize function references and avoid unnecessary rerenders or effect executions.
```

---

## Q5

Difference between Route and Navigate?

Answer:

```text
Route defines a URL path while Navigate moves the user to that path.
```

---

## Q6

Why is backend authentication still needed?

Answer:

```text
Frontend code can be bypassed, therefore backend endpoints must verify JWT tokens independently.
```

---

## Q7

What is Semantic Search?

Answer:

```text
Semantic search retrieves code using meaning rather than exact keyword matching by comparing embedding vectors.
```

---

## Q8

What is a Custom Hook?

Answer:

```text
A custom hook encapsulates reusable stateful logic using React hooks.
Examples:
useRepositories
useSearch
useQA
```

---
Semantic Search tells you:
Where code exists

QA tells you:
Ask questions about repository

ExplainCode tells you:
What this code does

# CodeSense Frontend Notes — Day 4 (June 23)

---

# FILE 1: LandingPage.jsx

## Purpose

Public marketing page shown before login.

Acts as:

```text
Website Homepage
        ↓
Show Product
        ↓
Explain Features
        ↓
Push User To Login
```

---

## Overall Flow

```text
User Opens Website
        ↓
LandingPage.jsx Loads
        ↓
Check AuthContext
        ↓
Is User Logged In?
      /     \
    Yes      No
     ↓        ↓
Dashboard   Landing Page
```

Code:

```js
const { authenticated } = useContext(AuthContext);

if(authenticated){
   return <Navigate to="/dashboard"/>
}
```

---

## Feature Cards Flow

```text
FeatureCard
      ↓
Receives Icon
Receives Title
Receives Description
      ↓
Renders Marketing Card
```

Example:

```js
<FeatureCard
   icon={Search}
   title="Semantic Search"
   desc="Search your codebase"
/>
```

---

## How It Works Flow

```text
Upload Repository
        ↓
CodeSense Parses
        ↓
Chunks Created
        ↓
Embeddings Generated
        ↓
AI Features Enabled
```

---

## Interview Questions

### Why check authentication inside LandingPage?

Answer:

```text
To prevent logged-in users from seeing the marketing page again.

Authenticated users are redirected directly to Dashboard.
```

---

### Difference between Navigate and Route?

Answer:

```text
Route:
Defines path-to-component mapping.

Navigate:
Programmatically redirects user.

Route = Road
Navigate = Vehicle
```

---

### Why use AuthContext here?

Answer:

```text
LandingPage needs global login state.

AuthContext provides authentication information
without prop drilling.
```

---

# FILE 2: DependencyGraph.jsx

---

## Purpose

Visualizes repository dependency relationships.

Real system:

```text
File A imports File B
File B imports File C

Graph:
A → B → C
```

Current version:

```text
Mostly Mock UI
```

---

## Overall Flow

```text
User Selects Repo
        ↓
useRepository(repoId)
        ↓
Check Status
        ↓
Ready?
      /   \
    No     Yes
    ↓       ↓
Wait     loadGraph()
```

---

## Graph Loading Flow

```text
loadGraph()
      ↓
dependencyApi.buildGraph()
      ↓
Backend Generates Graph
      ↓
Nodes + Edges Returned
      ↓
Frontend Draws Graph
```

Current code uses mocked metrics.

---

## Zoom Flow

```text
Zoom In Click
      ↓
setZoom(z+0.2)

Zoom Out Click
      ↓
setZoom(z-0.2)
```

---

## Pan Flow

```text
Mouse Down
      ↓
Start Drag
      ↓
Mouse Move
      ↓
Update Pan Coordinates
      ↓
Graph Moves
```

---

## Interview Questions

### Why use zoom state?

Answer:

```text
To dynamically scale graph rendering.
```

---

### Why use pan state?

Answer:

```text
To move graph viewport without modifying graph data.
```

---

### Why Dependency Graph?

Answer:

```text
Helps developers understand relationships
between modules and imports.
```

---

# FILE 3: ExplainCode.jsx

---

## Purpose

Explains code snippets using LLM.

---

## Overall Flow

```text
Paste Code
      ↓
Click Explain
      ↓
explainApi.explain()
      ↓
Backend LLM
      ↓
Explanation Returned
      ↓
UI Displays Result
```

---

## Explain Flow

```text
Code Input
      ↓
handleExplain()
      ↓
Validate Input
      ↓
API Call
      ↓
Response
      ↓
setExplanation()
```

---

## Why Paste Code?

Two modes exist:

### Semantic Search Mode

```text
Select Repo
      ↓
Find Existing Code
      ↓
Explain Returned Chunk
```

### Explain Code Mode

```text
Paste Any Snippet
      ↓
Get Explanation
```

No repository search required.

---

## Tabs Flow

```text
Summary
Detailed
Complexity
```

```text
Button Click
      ↓
setActiveTab()
      ↓
Conditional Rendering
```

---

## Interview Questions

### Why separate tabs?

Answer:

```text
Improves readability and prevents
information overload.
```

---

### Why use textarea?

Answer:

```text
Allows arbitrary code snippets
instead of selecting existing files.
```

---

### What does Explain Code do?

Answer:

```text
Sends code snippet to backend LLM service.

The LLM analyses purpose,
logic,
dependencies,
complexity,
and improvements.
```

---

# FILE 4: ImpactAnalysis.jsx

---

## Purpose

Determines blast radius of code changes.

---

## Real World Example

```text
Modify auth.py
      ↓
Which files break?
      ↓
Which services depend on it?
      ↓
Which APIs are affected?
```

---

## Overall Flow

```text
Select Repository
        ↓
Select File
        ↓
Analyze
        ↓
Backend Dependency Engine
        ↓
Affected Files Returned
```

---

## Blast Radius Flow

```text
Target File
      ↓
Direct Imports
      ↓
Indirect Imports
      ↓
Services
      ↓
External Consumers
```

---

## Visual Flow

```text
auth.py
   ↓
users.py
auth_service.py
   ↓
frontend
microservice
```

---

## Interview Questions

### What is Blast Radius?

Answer:

```text
The set of components affected by
a modification in a target file.
```

---

### Why is Impact Analysis useful?

Answer:

```text
Reduces deployment risk.

Developers know what might break
before changing code.
```

---

# FILE 5: Architecture.jsx

---

## Purpose

Generates high-level repository architecture.

---

## Overall Flow

```text
Select Repository
      ↓
architectureApi.summarise()
      ↓
Backend Analysis
      ↓
Architecture Summary
      ↓
Frontend Renders Report
```

---

## Architecture Generation Flow

```text
Repository
      ↓
AST Analysis
      ↓
Dependency Analysis
      ↓
Pattern Detection
      ↓
Architecture Summary
```

---

## Diagram Flow

```text
Frontend
     ↓
API Layer
     ↓
Services
   /     \
MongoDB  FAISS
```

---

## Architecture Sections

```text
Overview

Entry Points

Key Modules

Design Patterns

Dependencies

Recommendations
```

---

## Interview Questions

### Why Architecture Analysis?

Answer:

```text
Helps engineers understand
large repositories quickly.
```

---

### What are Entry Points?

Answer:

```text
Starting execution locations.

Examples:

main.py
app.py
index.js
server.js
```

---

### What are Key Modules?

Answer:

```text
Most important business logic components.
```

---

# FILE 6: AIReview.jsx

---

## Purpose

AI-powered code review system.

---

## Expected Flow

```text
Repository
      ↓
Analyze Code
      ↓
Security Review
      ↓
Performance Review
      ↓
Maintainability Review
      ↓
Final Score
```

---

## Review Pipeline

```text
Repository
      ↓
Parser
      ↓
Static Analysis
      ↓
LLM Review
      ↓
Recommendations
```

---

## Expected Metrics

```text
Code Quality

Security

Performance

Maintainability

Overall Score
```

---

## Interview Questions

### Why AI Review?

Answer:

```text
Automates initial code review.

Helps developers detect issues earlier.
```

---

### Difference between AI Review and Explain Code?

Answer:

```text
Explain Code:
Explains existing code.

AI Review:
Evaluates code quality and suggests improvements.
```

---

# Cross-File Architecture Questions

---

## Landing Page → Login Flow

```text
LandingPage
      ↓
Login
      ↓
Google OAuth
      ↓
Backend
      ↓
JWT
      ↓
Dashboard
```

---

## Dashboard → Search Flow

```text
Dashboard
      ↓
Search Button
      ↓
SemanticSearch
      ↓
Search API
      ↓
Backend Retrieval
      ↓
Results
```

---

## Dashboard → QA Flow

```text
Dashboard
      ↓
QA Page
      ↓
Question
      ↓
Backend
      ↓
RAG
      ↓
Answer
```

---

## Repository Analysis Flow

```text
Upload Repo
      ↓
Pipeline
      ↓
Chunking
      ↓
Embeddings
      ↓
FAISS
      ↓
Mongo
      ↓
Ready
```

---

# High Probability Interview Questions

### Explain entire frontend architecture.

```text
main.jsx
   ↓
App.jsx
   ↓
BrowserRouter
   ↓
ProtectedRoute
   ↓
AppShell
   ↓
Pages
   ↓
Hooks
   ↓
API Layer
   ↓
Backend
```

---

### Why use Hooks?

```text
Reusable stateful logic.

Avoid duplicate code.
```

---

### Why use Context?

```text
Global shared state.

Authentication available everywhere.
```

---

### Why use Custom Hooks?

```text
Separate business logic
from UI components.
```

---

### Why use ProtectedRoute?

```text
Prevents unauthorized users
from accessing internal pages.
```

---

### What is the complete CodeSense user journey?

```text
Login
  ↓
Dashboard
  ↓
Upload Repository
  ↓
Backend Pipeline
  ↓
Index Ready
  ↓
Search
  ↓
QA
  ↓
Explain
  ↓
Architecture
  ↓
Impact Analysis
  ↓
AI Review
```
