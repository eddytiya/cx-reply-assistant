import { useRef, useState } from "react";
import { api, useLoad } from "../api";
import ReplyPanel from "./ReplyPanel";

function date(value) {
  return value ? new Date(value).toLocaleString() : "Not available";
}

export default function Workspace({ brand, mode }) {
  const list = useLoad(`/brands/${brand.id}/conversations`, true);
  const [selectedId, setSelectedId] = useState("");
  const conversationId = selectedId || list.data?.[0]?.id;

  return (
    <section className="panel">
      <div className="heading-row">
        <h2>{brand.name} conversations</h2>
        <button onClick={list.refresh} disabled={list.loading}>
          Refresh list
        </button>
      </div>

      {list.loading && <p role="status">Loading conversations...</p>}
      {list.error && <p className="error" role="alert">{list.error}</p>}

      {!list.loading && !list.error && (
        list.data.length ? (
          <div className="conversation-layout">
            <nav className="conversation-list" aria-label="Conversations">
              {list.data.map((item, index) => (
                <button
                  key={item.id}
                  aria-pressed={conversationId === item.id}
                  onClick={() => setSelectedId(item.id)}
                >
                  <strong>Conversation {index + 1}</strong>
                  <span>{item.status}</span>
                  <small>{date(item.created_at)}</small>
                </button>
              ))}
            </nav>

            <Conversation
              key={conversationId}
              brandId={brand.id}
              conversationId={conversationId}
              mode={mode}
            />
          </div>
        ) : (
          <p>No conversations found.</p>
        )
      )}
    </section>
  );
}

function Conversation({ brandId, conversationId, mode }) {
  const path = `/brands/${brandId}/conversations/${conversationId}`;
  const detail = useLoad(path);

  if (detail.loading) {
    return <p role="status">Loading conversation...</p>;
  }

  if (detail.error) {
    return (
      <div>
        <p className="error" role="alert">{detail.error}</p>
        <button onClick={detail.refresh}>Retry</button>
      </div>
    );
  }

  const data = detail.data;
  const closed = data.conversation.status !== "open";

  return (
    <div className="conversation-detail">
      <div className="heading-row">
        <h2>{mode === "customer" ? "Customer view" : "Agent workspace"}</h2>
        <button onClick={detail.refresh}>Refresh conversation</button>
      </div>

      <div className="context-grid">
        <section className="context-card">
          <h3>Customer</h3>
          <p><strong>{data.customer.name}</strong></p>
          <p>{data.customer.email || "No email provided"}</p>
          <p>Brand: {data.brand.name}</p>
          <p>Conversation: {data.conversation.status}</p>
        </section>

        <section className="context-card">
          <h3>Order</h3>
          {data.order ? (
            <>
              <p><strong>{data.order.order_number}</strong></p>
              <p>{data.order.item_name}</p>
              <p>Status: {data.order.status}</p>
              <p>Delivered: {date(data.order.delivered_at)}</p>
            </>
          ) : (
            <p>No linked order.</p>
          )}
        </section>
      </div>

      <section className="latest-message">
        <h3>Latest customer message</h3>
        <p>{data.latest_customer_message?.content || "No customer message yet."}</p>
      </section>

      <h3>Conversation history</h3>
      <ol className="message-list">
        {data.messages.map((message) => (
          <li key={message.id} className={`message ${message.sender_role}`}>
            <div className="heading-row">
              <strong>
                {message.sender_role === "customer"
                  ? data.customer.name
                  : "Support agent"}
              </strong>
              <time dateTime={message.created_at}>{date(message.created_at)}</time>
            </div>
            <p>{message.content}</p>
          </li>
        ))}
      </ol>

      {!data.messages.length && <p>No messages yet.</p>}

      <Composer
        key={mode}
        path={path}
        role={mode}
        closed={closed}
        onSaved={detail.refresh}
      />

      {mode === "agent" && (
        <ReplyPanel
          path={path}
          latestCustomerId={data.latest_customer_message?.id}
          closed={closed}
          onSent={detail.refresh}
        />
      )}
    </div>
  );
}

function Composer({ path, role, closed, onSaved }) {
  const [content, setContent] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const lock = useRef(false);

  async function send(event) {
    event.preventDefault();
    if (lock.current || closed || !content.trim()) return;

    lock.current = true;
    setBusy(true);
    setError("");

    try {
      await api(`${path}/messages`, {
        method: "POST",
        body: { sender_role: role, content: content.trim() },
      });
      setContent("");
      onSaved();
    } catch (error) {
      setError(error.message);
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }

  return (
    <form className="subpanel" onSubmit={send}>
      <h3>{role === "customer" ? "Send a customer message" : "Send a manual reply"}</h3>

      <label>
        Message
        <textarea
          value={content}
          onChange={(event) => setContent(event.target.value)}
          rows={4}
          maxLength={5000}
          required
          disabled={busy || closed}
        />
      </label>

      <div className="heading-row">
        <small>{content.length} / 5,000 characters</small>
        <button className="primary" disabled={busy || closed || !content.trim()}>
          {busy ? "Sending..." : `Send as ${role}`}
        </button>
      </div>

      {closed && <p>This conversation is closed.</p>}
      {error && <p className="error" role="alert">{error}</p>}
    </form>
  );
}