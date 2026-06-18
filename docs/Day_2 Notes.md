Day 2 Objective

Master Frontend Structure.

By the end of Day 2 I should be able to explain:

How React starts
How routing works
How authentication works
How layouts work
How pages are rendered
How frontend communicates with backend
How repositories flow through the application
Files Covered
Entry Layer
src/index.js
Routing Layer
src/App.jsx
Layout Layer
src/components/layout/AppShell.jsx
src/components/layout/Sidebar.jsx
Page Layer
src/pages/Dashboard.jsx
Hook Layer
src/hooks/useRepositories.js
API Layer
src/services/api.js

Covered from uploaded code.

Frontend Architecture
index.js
    ↓
App.jsx
    ↓
BrowserRouter
    ↓
ProtectedRoute
    ↓
AppShell
    ├── Sidebar
    └── Current Page
            ↓
       Dashboard
       Upload
       Search
       QA
       Explain
       Graph
       Impact
       Review
       Architecture
React Fundamentals Learned
What is React?

React is a JavaScript library used to build user interfaces.

React allows UI to be built using reusable components.

Example:

<Sidebar />
<Dashboard />
<UploadPage />
Library vs Framework
Library
You call the library.

Example:

React

You decide:

Routing
Folder Structure
State Management
Architecture
Framework
Framework calls your code.

Example:

Angular

Framework imposes structure.

DOM

DOM = Document Object Model

Browser representation of HTML.

Example:

<body>
  <div id="root"></div>
</body>

DOM Tree:

Document
 └── body
      └── div#root

React eventually renders into the DOM.

index.js

Purpose:

Application entry point.

Code Flow:

Browser
 ↓
index.html
 ↓
root div
 ↓
ReactDOM
 ↓
<App />

Key Line:

ReactDOM.createRoot(
    document.getElementById("root")
);

Meaning:

Create React rendering root.
App.jsx

Purpose:

Routing + Authentication Layer

Responsibilities:

Route Management
Protected Routes
Toast Notifications
Layout Selection
Routing
<Route path="/" element={<Dashboard />} />

Meaning:

URL
↓
Page

Example:

/upload
↓
UploadPage
BrowserRouter

Purpose:

Enable URL-based navigation.

Without it:

/upload
/search
/qa

would not work.

ProtectedRoute

Purpose:

Protect authenticated pages.

Flow:

User Opens Page
       ↓
localStorage
       ↓
access_token exists?
       ↓

YES → Continue

NO → Redirect Login
localStorage

Purpose:

Browser-side storage.

Used for:

access_token
refresh_token
user

Example:

localStorage.setItem(
  "access_token",
  token
);
React Children

Concept learned today.

Example:

<AppShell>
   <Routes />
</AppShell>

React internally:

AppShell({
   children: <Routes />
})

Therefore:

{children}

renders:

<Routes />
AppShell.jsx

Purpose:

Common Layout Wrapper

Architecture:

Sidebar
     +
Main Content Area

Structure:

+-----------+----------------+
| Sidebar   | Current Page   |
+-----------+----------------+
Why AppShell Exists

Without AppShell:

Sidebar repeated everywhere.

With AppShell:

Single reusable layout.
Sidebar.jsx

Purpose:

Navigation Layer

Responsibilities:

Navigation
Active Route Highlighting
Collapse/Expand
User Info
Logout
useLocation()

Purpose:

Read current URL.

Example:

/search

returns:

location.pathname
NavLink

Purpose:

Navigation without page reload.

Example:

<NavLink to="/upload">
Sidebar State
const [collapsed,setCollapsed]

Meaning:

Sidebar expanded?
Sidebar collapsed?
Dashboard.jsx

Purpose:

Application Home Page

Responsibilities:

System Health
Repository Statistics
Quick Actions
Recent Repositories
useState

Purpose:

Store changing values.

Example:

const [health,setHealth]
useEffect

Purpose:

Run code after component renders.

Example:

useEffect(() => {
   healthApi.ping();
}, []);

Meaning:

Run once when page loads.
Dashboard Data Flow
Dashboard
 ↓
useRepositories()
 ↓
repositoriesApi
 ↓
Backend
 ↓
Data
 ↓
UI
Quick Actions

Purpose:

Navigation shortcuts.

Examples:

Upload Repo
Semantic Search
Repo QA
Explain Code
Dependency Graph
Architecture
React Array Methods Learned
map()

Purpose:

Create UI from arrays.

JavaScript:

repos.map(...)

Equivalent C++:

for(auto r : repos)
filter()

Purpose:

Keep matching items.

Example:

repos.filter(
 r => r.status === "ready"
)
reduce()

Purpose:

Aggregate values.

Example:

repos.reduce(...)

Equivalent:

total += value;
Data Flow Explained

Question:

How does RepoRow know repo.id?

Answer:

Backend
 ↓
useRepositories()
 ↓
repos[]
 ↓
Dashboard
 ↓
RepoRow(repo)

RepoRow receives repo through props.

Custom Hooks
useRepositories()

Purpose:

Central repository state manager.

Location:

hooks/useRepositories.js

Covered from uploaded file.

Why Custom Hook Exists

Without it:

Every page fetches repositories itself.

With hook:

Single reusable repository logic.
Repository Polling

Discovered today.

Statuses:

pending
cloning
parsing
chunking
embedding
indexing
processing

When repository is processing:

Auto-refresh every few seconds.

Flow:

Repository Processing
 ↓
useRepositories
 ↓
setInterval
 ↓
Fetch Again
 ↓
Update UI

This is why Dashboard updates automatically.

API Layer
api.js

Purpose:

Frontend ↔ Backend Communication

Covered from uploaded file.

Axios

Purpose:

Send HTTP requests.

Example:

axios.get(...)
axios.post(...)
BASE_URL
Frontend API Gateway

Current:

https://codesense-backend-18lv.onrender.com/api/v1

Request Interceptor

Purpose:

Automatically attach JWT token.

Flow:

Request
 ↓
Read access_token
 ↓
Authorization Header
 ↓
Backend
Response Interceptor

Purpose:

Handle token refresh.

Flow:

Request
 ↓
401 Unauthorized
 ↓
Refresh Token
 ↓
Get New Access Token
 ↓
Retry Request

If refresh fails:

Clear Tokens
 ↓
Login Page

API Groups
repositoriesApi

Responsibilities:

List repositories
Get repository
Get files
Get chunks
GitHub ingestion
ZIP upload
Delete repository
searchApi

Responsibilities:

Semantic Search
Batch Search
Embedding Info
qaApi

Responsibilities:

Repository Question Answering
explainApi

Responsibilities:

Code Explanation
dependencyApi

Responsibilities:

Dependency Graph
impactApi

Responsibilities:

Impact Analysis
reviewApi

Responsibilities:

AI Code Review
architectureApi

Responsibilities:

Architecture Summary
healthApi

Responsibilities:

Backend Health Check
authApi

Responsibilities:

Google Login
Token Refresh
Current User
Authentication Flow
User
 ↓
Login
 ↓
Google Token
 ↓
authApi.loginGoogle()
 ↓
Backend
 ↓
access_token
refresh_token
 ↓
localStorage
 ↓
ProtectedRoute
 ↓
Application Access
Tailwind CSS Concepts Learned
flex
Horizontal Layout
flex-1
Take remaining space
grid
Grid Layout
gap
Spacing between elements
p-*
Padding
m-*
Margin
bg-*
Background color
text-*
Text styling
rounded-*
Rounded corners
hover:*
Hover effect
overflow-y-auto
Scrollable content area
Export vs Export Default
export

Named export.

Example:

export function add(){}

Import:

import { add } from "./file";
export default

Default export.

Example:

export default AppShell;

Import:

import AppShell from "./file";
Interview Questions
Q1

What is AppShell?

Answer

AppShell is a shared layout component that wraps authenticated pages and provides common UI such as Sidebar and Main Content Area.

Q2

What is ProtectedRoute?

Answer

ProtectedRoute checks authentication status using access_token stored in localStorage and redirects unauthenticated users to Login.

Q3

Why use a custom hook?

Answer

To centralize reusable state management and API logic.

Q4

Why use Axios interceptors?

Answer

To automatically attach JWT tokens and handle token refresh logic globally.

Q5

How does Dashboard get repository data?

Answer
Dashboard
 ↓
useRepositories()
 ↓
repositoriesApi.list()
 ↓
Backend
 ↓
Response
Common Mistakes
Mistake 1

Thinking children comes from the current file.

Reality:

children comes from the parent component.
Mistake 2

Thinking export default is required for same-file usage.

Reality:

Functions work in same file without export.
Export only enables other files to import it.
Mistake 3

Thinking RepoRow fetches data.

Reality:

RepoRow only receives props.
Dashboard fetches data.
Recruiter Explanation (15 sec)

Code Sense is a React-based AI repository intelligence platform. The frontend uses React Router, protected routes, reusable layouts, custom hooks, and an API layer to interact with a FastAPI backend that provides semantic search, repository Q&A, architecture analysis, dependency visualization, and AI-assisted code understanding.

Engineer Explanation (30 sec)

The frontend follows a layered architecture consisting of pages, reusable components, custom hooks, and an API abstraction layer. Authentication is JWT-based, routing is handled by React Router, repository state is centralized through custom hooks, and Axios interceptors manage token refresh and error normalization. The UI exposes repository ingestion, semantic search, RAG-based Q&A, dependency analysis, architecture summaries, and AI code review capabilities.

package.json

Purpose:

Project configuration file.

Contains:

Project Name
Version
Scripts
Dependencies
DevDependencies

Example:

{
  "scripts": {
    "dev": "vite"
  }
}
Scripts

Purpose:

Shortcuts for common development tasks.

Examples:

npm run dev
npm run build
npm run preview

Think:

Scripts
=
Frequently used commands given easy names.
Dependencies

Purpose:

External libraries required by the project.

Examples:

react
axios
react-router-dom
lucide-react

Think:

Dependencies
=
Packages the project needs to run.
package-lock.json

Purpose:

Records exact installed dependency versions.

Automatically generated by:

npm install
package.json vs package-lock.json
package.json
What we want.

Example:

"axios": "^1.9.0"

Meaning:

Any compatible Axios version.
package-lock.json
What we actually installed.

Example:

axios 1.9.0

exactly.

Why package-lock.json exists

Without it:

Developer A
↓
axios 1.9.0

Developer B
↓
axios 1.9.3

Different environments.

Possible bugs.

With it:

Everyone installs
the exact same dependency tree.
Interview Answer

package.json defines project metadata, scripts, and dependency requirements. package-lock.json records the exact dependency versions that were installed, ensuring consistent builds across different machines.

DOM = Document Object Model

The browser converts HTML into a tree-like structure called the DOM.

Example HTML:

<body>
  <div id="root">
    <h1>Hello</h1>
  </div>
</body>

Browser internally creates:

Document
 └── body
      └── div
           └── h1

This tree is called the DOM.

Why DOM Exists

The browser needs a way to:

Read HTML
Modify HTML
Add Elements
Delete Elements
Change Text

Example:

document.getElementById("root")

This accesses a DOM element.

Interview Answer

The DOM (Document Object Model) is the browser's tree representation of an HTML document. JavaScript and React interact with the DOM to update what users see on the screen.

What is ReactDOM?

ReactDOM is the bridge between:

React Components
        ↓
Browser DOM

React itself only knows:

<App />
<Sidebar />
<Dashboard />

These are JavaScript components.

The browser cannot display React components directly.

ReactDOM converts them into real DOM elements.

Example

Code:

function App() {
  return <h1>Hello</h1>;
}

React understands:

Component App

Browser understands:

<h1>Hello</h1>

ReactDOM performs the conversion.

Code Sense Example
const root = ReactDOM.createRoot(
  document.getElementById("root")
);

Meaning:

Find root DOM element
↓
Create React rendering area
root.render(<App />);

Meaning:

Render App component
inside root DOM element
Flow
App Component
      ↓
ReactDOM
      ↓
Browser DOM
      ↓
User Screen
Interview Answer

ReactDOM is the library responsible for rendering React components into the browser's DOM. It acts as the bridge between React code and the actual webpage displayed to users.

Library vs Framework

This is one of the most common interview questions.

Library

A library provides functionality that your code can call when needed.

Your Code
    ↓
Calls Library

Example:

React
Axios
Lodash
React Example

You decide:

Folder Structure
Routing
Authentication
API Layer
State Management

React does not force these decisions.

React simply provides tools.

Control Flow
Your Code
      ↓
Calls React

You remain in control.

Framework

A framework provides structure and calls your code.

Framework
      ↓
Calls Your Code

Examples:

Angular
Ruby on Rails
Django
Framework Example

Framework decides:

Project Structure
Routing Style
Application Lifecycle

You follow its conventions.

Control Flow
Framework
      ↓
Calls Your Code

Framework remains in control.

Comparison
Library	Framework
Provides tools	Provides structure
You call it	It calls your code
More flexibility	More conventions
Easier to adopt gradually	Requires following framework patterns
Example: React	Example: Angular
Memory Trick
Library
=
I am in control

Framework
=
Framework is in control
React Is A Library

Why?

Because React does NOT force:

Routing
Folder Structure
State Management
API Layer
Authentication

In Code Sense:

You chose:
React Router
Axios
Custom Hooks
Custom Folder Structure

React did not enforce those choices.

Therefore:

React = Library
Interview Answers
What is DOM?

DOM is the browser's tree representation of an HTML document. JavaScript and React manipulate the DOM to update the user interface.

What is ReactDOM?

ReactDOM is responsible for rendering React components into the browser DOM. It acts as the bridge between React code and the actual webpage.

Difference Between Library and Framework?

A library is called by your code, while a framework calls your code. React is a library because developers decide how to structure and use the application, whereas frameworks impose more conventions and control the application flow.