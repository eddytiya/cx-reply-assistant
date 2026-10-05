import { useEffect, useState } from "react";
import MessageComposer from "./MessageComposer";

function formatDate(value) {
  return new Date(value).toLocaleString();
}

export default function ConversationBrowser({ brand }) {
  const [conversations, setConversations] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    async function loadConversations() {
      try {
        const response = await fetch(
          `/api/brands/${brand.id}/conversations`,
          { signal: controller.signal }
        );

        if (!response.ok) {
          throw new Error(
            `Could not load conversations (${response.status}).`
          );
        }

        const data = await response.json();

        if (!controller.signal.aborted) {
          setConversations(data);
          setSelectedId(data[0]?.id ?? "");
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(err.message);
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    loadConversations();

    return () => controller.abort();
  }, [brand.id]);

  return (
    <section className="panel">
      <h2>{brand.name} conversations</h2>

      {loading && <p role="status">Loading conversations...</p>}

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      {!loading && !error && conversations.length === 0 && (
        <p>No conversations found for this brand.</p>
      )}

      {!loading && !error && conversations.length > 0 && (
        <div className="conversation-layout">
          <nav className="conversation-list" aria-label="Conversations">
            {conversations.map((conversation, index) => (
              <button
                key={conversation.id}
                type="button"
                className={`conversation-button ${
                  selectedId === conversation.id ? "selected" : ""
                }`}
                aria-pressed={selectedId === conversation.id}
                onClick={() => setSelectedId(conversation.id)}
              >
                <strong>Conversation {index + 1}</strong>
                <span>{conversation.status}</span>
                <small>{formatDate(conversation.created_at)}</small>
              </button>
            ))}
          </nav>

          {selectedId && (
            <ConversationDetail
              key={`${brand.id}:${selectedId}`}
              brandId={brand.id}
              conversationId={selectedId}
            />
          )}
        </div>
      )}
    </section>
  );
}

function ConversationDetail({ brandId, conversationId }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function handleMessageSaved(savedMessage) {
    setDetail((current) => {
      if (!current) {
        return current;
      }

      const alreadyDisplayed = current.messages.some(
        (message) => message.id === savedMessage.id
      );

      if (alreadyDisplayed) {
        return current;
      }

      return {
        ...current,
        messages: [...current.messages, savedMessage],
        latest_customer_message:
          savedMessage.sender_role === "customer"
            ? savedMessage
            : current.latest_customer_message,
      };
    });
  }

  useEffect(() => {
    const controller = new AbortController();

    async function loadDetail() {
      try {
        const response = await fetch(
          `/api/brands/${brandId}/conversations/${conversationId}`,
          { signal: controller.signal }
        );

        if (!response.ok) {
          throw new Error(
            `Could not load conversation details (${response.status}).`
          );
        }

        const data = await response.json();

        if (!controller.signal.aborted) {
          setDetail(data);
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(err.message);
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    loadDetail();

    return () => controller.abort();
  }, [brandId, conversationId]);

  if (loading) {
    return <p role="status">Loading conversation details...</p>;
  }

  if (error) {
    return (
      <p className="error" role="alert">
        {error}
      </p>
    );
  }

  if (!detail) {
    return <p>No conversation details available.</p>;
  }

  return (
    <div className="conversation-detail">
      <div className="context-grid">
        <section className="context-card">
          <h3>Customer</h3>

          <p>
            <strong>{detail.customer.name}</strong>
          </p>

          <p>{detail.customer.email || "No email provided"}</p>
          <p>Brand: {detail.brand.name}</p>
          <p>Conversation: {detail.conversation.status}</p>
        </section>

        <section className="context-card">
          <h3>Order</h3>

          {detail.order ? (
            <>
              <p>
                <strong>{detail.order.order_number}</strong>
              </p>

              <p>{detail.order.item_name}</p>
              <p>Status: {detail.order.status}</p>

              <p>
                Delivered:{" "}
                {detail.order.delivered_at
                  ? formatDate(detail.order.delivered_at)
                  : "No delivery date"}
              </p>
            </>
          ) : (
            <p>No order linked to this conversation.</p>
          )}
        </section>
      </div>

      <section
        className="latest-message"
        aria-labelledby="latest-message-title"
      >
        <h3 id="latest-message-title">Latest customer message</h3>

        {detail.latest_customer_message ? (
          <>
            <p>{detail.latest_customer_message.content}</p>

            <time dateTime={detail.latest_customer_message.created_at}>
              {formatDate(detail.latest_customer_message.created_at)}
            </time>
          </>
        ) : (
          <p>No customer message yet.</p>
        )}
      </section>

      <h3>Messages</h3>

      {detail.messages.length === 0 ? (
        <p>No messages yet.</p>
      ) : (
        <ol className="message-list" aria-label="Message history">
          {detail.messages.map((message) => (
            <li
              key={message.id}
              className={`message ${message.sender_role}`}
            >
              <div className="message-heading">
                <strong>
                  {message.sender_role === "customer"
                    ? detail.customer.name
                    : "Support agent"}
                </strong>

                <time dateTime={message.created_at}>
                  {formatDate(message.created_at)}
                </time>
              </div>

              <p>{message.content}</p>
            </li>
          ))}
        </ol>
      )}

      <MessageComposer
        brandId={brandId}
        conversationId={conversationId}
        conversationStatus={detail.conversation.status}
        onMessageSaved={handleMessageSaved}
      />
    </div>
  );
}