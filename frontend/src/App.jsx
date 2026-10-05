import { useState } from "react";
import { useLoad } from "./api";
import Workspace from "./components/Workspace";
import KnowledgeManager from "./components/KnowledgeManager";

export default function App({ user }) {
  const brands = useLoad("/brands", true);
  const [brandId, setBrandId] = useState(user.brand_id || "");
  const [mode, setMode] = useState(user.role === "admin" ? "agent" : "customer");
  const [tab, setTab] = useState("conversation");

  const brand = brands.data?.find((item) => item.id === brandId);

  function changeMode(nextMode) {
    setMode(nextMode);
    setTab("conversation");
  }

  return (
    <main className="app">
      <header className="page-header">
        <p className="eyebrow">CUSTOMER SUPPORT</p>
        <h1>CX Reply Assistant</h1>
        <p>Brand-specific support with AI drafts reviewed by an agent.</p>
      </header>

      <section className="panel toolbar">
        <label>
          Brand
          <select
            value={brandId}
            onChange={(event) => setBrandId(event.target.value)}
            disabled={brands.loading}
          >
            <option value="">Select a brand</option>
            {(brands.data || []).map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>

        {user.role === "admin" && <div className="tabs" role="group" aria-label="Conversation view">
          <button
            type="button"
            aria-pressed={mode === "customer"}
            onClick={() => changeMode("customer")}
          >
            Customer view
          </button>
          <button
            type="button"
            aria-pressed={mode === "agent"}
            onClick={() => changeMode("agent")}
          >
            Agent view
          </button>
        </div>}

        {brands.loading && <p role="status">Loading brands...</p>}
        {brands.error && (
          <div role="alert">
            <p className="error">{brands.error}</p>
            <button onClick={brands.refresh}>Retry</button>
          </div>
        )}
      </section>

      {brand ? (
        <>
          {user.role === "admin" && mode === "agent" && (
            <nav className="tabs section-tabs" aria-label="Agent sections">
              <button
                aria-pressed={tab === "conversation"}
                onClick={() => setTab("conversation")}
              >
                Conversations
              </button>
              <button
                aria-pressed={tab === "policies"}
                onClick={() => setTab("policies")}
              >
                Manage policies
              </button>
            </nav>
          )}

          {user.role === "admin" && mode === "agent" && tab === "policies" ? (
            <KnowledgeManager key={brand.id} brand={brand} />
          ) : (
            <Workspace key={brand.id} brand={brand} mode={mode} />
          )}
        </>
      ) : (
        <p className="muted">Select a brand to begin.</p>
      )}
    </main>
  );
}
