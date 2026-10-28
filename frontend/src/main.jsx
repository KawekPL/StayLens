import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";

class ErrorBoundary extends React.Component {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <main className="loading-state">
        <h1>Nie udało się wyświetlić aplikacji</h1>
        <p>Odśwież podgląd, aby spróbować ponownie.</p>
        <button
          className="primary-button"
          onClick={() => window.location.reload()}
        >
          Odśwież podgląd
        </button>
      </main>
    ) : (
      this.props.children
    );
  }
}

createRoot(document.getElementById("root")).render(
  <ErrorBoundary>
    <App />
  </ErrorBoundary>,
);
