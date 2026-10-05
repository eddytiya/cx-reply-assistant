import { useRef, useState } from "react";
import { api, useLoad } from "../api";

export default function ReplyPanel({
  path,
  latestCustomerId,
  closed,
  onSent,
}) {
  const endpoint = `${path}/reply-generations`;
  const history = useLoad(endpoint, true);
  const [selectedId, setSelectedId] = useState("");
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const lock = useRef(false);

  const records = history.data || [];
  const selected =
    records.find((record) => record.id === selectedId) || records[0];

  async function generate() {
    if (lock.current || closed || !latestCustomerId) return;

    if (!window.confirm(
      "Generate a new draft for the latest customer message? Unsaved draft edits will be discarded."
    )) return;

    lock.current = true;
    setGenerating(true);
    setError("");

    try {
      const record = await api(endpoint, { method: "POST" });
      setSelectedId(record.id);
    } catch (error) {
      setError(error.message);
    } finally {
      history.refresh();
      lock.current = false;
      setGenerating(false);
    }
  }

  return (
    <section className="subpanel">
      <div className="heading-row">
        <h3>AI reply assistant</h3>
        <button
          className="primary"
          onClick={generate}
          disabled={generating || history.loading || closed || !latestCustomerId}
        >
          {generating ? "Generating..." : records.length ? "Regenerate reply" : "Generate reply"}
        </button>
      </div>

      <p className="muted">
        Review the draft and supporting policies before sending.
      </p>

      {!latestCustomerId && <p>A customer message is needed first.</p>}
      {closed && <p>This conversation is closed.</p>}
      {error && <p className="error" role="alert">{error}</p>}

      {history.loading && <p role="status">Loading generation history...</p>}

      {history.error && (
        <div role="alert">
          <p className="error">{history.error}</p>
          <button onClick={history.refresh}>Reload history</button>
        </div>
      )}

      {!history.loading && !history.error && (
        <>
          {records.length > 0 ? (
            <>
              <label>
                Generation history
                <select
                  value={selected.id}
                  disabled={generating}
                  onChange={(event) => {
                    if (window.confirm(
                      "Open this draft? Unsaved edits will be discarded."
                    )) {
                      setSelectedId(event.target.value);
                    }
                  }}
                >
                  {records.map((record) => (
                    <option key={record.id} value={record.id}>
                      {new Date(record.created_at).toLocaleString()} — {record.status}
                    </option>
                  ))}
                </select>
              </label>

              <DraftEditor
                key={`${selected.id}:${selected.updated_at}`}
                draft={selected}
                endpoint={endpoint}
                latestCustomerId={latestCustomerId}
                closed={closed}
                generating={generating}
                onSaved={history.refresh}
                onSent={onSent}
              />
            </>
          ) : (
            <p>No drafts yet. Click Generate reply to create one.</p>
          )}
        </>
      )}
    </section>
  );
}

function DraftEditor({
  draft,
  endpoint,
  latestCustomerId,
  closed,
  generating,
  onSaved,
  onSent,
}) {
  const savedText = draft.agent_edited_response ?? draft.ai_response ?? "";
  const [text, setText] = useState(savedText);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [reviewed, setReviewed] = useState(false);
  const lock = useRef(false);

  const snapshot = draft.context_snapshot || {};
  const result = snapshot.generation_result || {};
  const retrieval = snapshot.retrieval || {};
  const policies = retrieval.entries || [];

  const sent = draft.status === "sent";
  const failed = draft.status === "failed";
  const needsReview = draft.status === "needs_review";
  const stale = draft.customer_message_id !== latestCustomerId;
  const disabled = busy || generating || closed || sent || failed || stale;
  const dirty = text !== savedText;

  async function saveOrApprove(approve) {
    if (lock.current || disabled || !text.trim()) return;
    if (approve && needsReview && !reviewed) return;

    lock.current = true;
    setBusy(true);
    setError("");

    try {
      if (dirty) {
        await api(`${endpoint}/${draft.id}/edit`, {
          method: "PUT",
          body: { content: text.trim() },
        });
      }

      if (approve) {
        await api(`${endpoint}/${draft.id}/approve`, { method: "POST" });
        onSent();
      } else {
        onSaved();
      }
    } catch (error) {
      setError(error.message);
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }

  return (
    <div className="draft-editor">
      <p>
        <strong>Status:</strong> {draft.status}
        {" · "}
        {result.model_called === false ? "Guardrail fallback" : draft.model_name}
      </p>

      <p><strong>Customer message used:</strong> {draft.customer_message_snapshot}</p>

      {stale && !sent && (
        <p className="warning">
          A newer customer message exists. Generate a new draft before sending.
        </p>
      )}

      {(needsReview || failed) && (
        <div className="warning" role="status">
          <strong>{failed ? "Generation failed" : "Agent review required"}</strong>
          <p>{result.review_reason || "Review the available information carefully."}</p>
          {draft.error_code && <small>{draft.error_code}</small>}
          {failed && <p>You can regenerate or send a manual reply.</p>}
        </div>
      )}

      <label>
        {sent ? "Sent reply" : "Draft reply"}
        <textarea
          rows={7}
          maxLength={5000}
          value={sent ? draft.final_response || "" : text}
          disabled={disabled}
          onChange={(event) => {
            setText(event.target.value);
            setReviewed(false);
          }}
        />
      </label>

      {!sent && !failed && (
        <>
          {needsReview && (
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={reviewed}
                disabled={disabled}
                onChange={(event) => setReviewed(event.target.checked)}
              />
              I have reviewed the warning and the reply.
            </label>
          )}

          <div className="actions">
            <button
              onClick={() => saveOrApprove(false)}
              disabled={disabled || !text.trim() || !dirty}
            >
              Save edits
            </button>
            <button
              className="primary"
              onClick={() => saveOrApprove(true)}
              disabled={disabled || !text.trim() || (needsReview && !reviewed)}
            >
              {busy ? "Saving..." : "Approve and send"}
            </button>
          </div>
        </>
      )}

      {sent && <p className="success">This reply has been sent.</p>}
      {error && <p className="error" role="alert">{error}</p>}

      <details className="context-details">
        <summary>Original AI / fallback draft</summary>
        <p className="preserve">{draft.ai_response || "No draft was produced."}</p>
      </details>

      <details className="context-details" open>
        <summary>Retrieved policies and context</summary>

        <p><strong>Brand:</strong> {snapshot.brand?.name || "Unavailable"}</p>
        <p>
          <strong>Order:</strong>{" "}
          {snapshot.order?.order_number || "No linked order"}
          {snapshot.order && ` — ${snapshot.order.status}`}
        </p>

        {retrieval.reason && <p>{retrieval.reason}</p>}

        {policies.length ? policies.map((policy) => (
          <article className="policy-card" key={policy.id}>
            <strong>{policy.title}</strong>
            <p className="muted">
              {policy.category}
              {result.used_policy_ids?.includes(policy.id)
                ? " · Cited by model"
                : " · Retrieved context"}
            </p>
            <p className="preserve">{policy.content}</p>
          </article>
        )) : (
          <p>No relevant policies were retrieved.</p>
        )}

        <details>
          <summary>Full saved context</summary>
          <pre>{JSON.stringify(snapshot, null, 2)}</pre>
        </details>
      </details>
    </div>
  );
}