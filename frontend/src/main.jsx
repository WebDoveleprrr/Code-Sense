// src/index.js --- starts whole frontend
import React from "react"; //react req for jsx
import ReactDOM from "react-dom/client"; //needed for react to make changes to browser
import "./index.css"; //global styling
import App from "./App"; //imports whole application
import { GoogleOAuthProvider } from "@react-oauth/google"; //google login

const root = ReactDOM.createRoot(document.getElementById("root")); //create root which exists inside index.html
root.render( //starts react app
  <GoogleOAuthProvider clientId={import.meta.env.VITE_GOOGLE_CLIENT_ID || ""}>
    <App />  //wraps whole application
  </GoogleOAuthProvider>
);