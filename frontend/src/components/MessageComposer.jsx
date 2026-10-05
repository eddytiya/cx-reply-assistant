import { useRef, useState } from "react";

export default function MessageComposer({
  brandId,
  conversationId,
  conversationStatus,
  onMessageSaved,
}) {
  const [senderRole, setSenderRole] = useState("customer");
  const [content, setContent] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const submissionInProgress = useRef(false);
  const isClosed = conversationStatus !== "open";

  async function handleSubmit(event) {
    event.preventDefault();

    const cleanedContent = content.trim();

    if (submissionInProgress.current || isClosed) {
      return;
    }

    setError("");
    setSuccess("");

    if (!cleanedContent) {
      setError("Please enter a message.");
      return;
    }

    if (cleanedContent.length > 5000) {
      setError("Your message must contain no more than 5,000 characters.");
      return;
    }

    submissionInProgress.current = true;
    setSending(true);

    try {
      const response = await fetch(
        `/api/brands/${brandId}/conversations/${conversationId}/messages`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            sender_role: senderRole,
            content: cleanedContent,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        let message = `Could not send message (${response.status}).`;

        if (typeof data.detail === "string") {
          message = data.detail;
        } else if (Array.isArray(data.detail)) {
          message = data.detail.map((item) => item.msg).join(" ");
        }

        throw new Error(message);
      }

      onMessageSaved(data);
      setContent("");
      setSuccess("Message saved to the conversation.");
    } catch (err) {
      setError(
        err instanceof TypeError
          ? "Connection interrupted. Refresh the conversation to check whether the message was saved before sending again."
          : err.message || "Could not send the message."
      );
    } finally {
      submissionInProgress.current = false;
      setSending(false);
    }
  }

  function changeRole(role) {
    setSenderRole(role);
    setContent("");
    setError("");
    setSuccess("");
  }

  return (
    <form className="message-composer" onSubmit={handleSubmit}>
      <h3>Write a message</h3>

      <div className="role-toggle" role="group" aria-label="Send message as">
        <button
          type="button"
          className={senderRole === "customer" ? "active" : ""}
          aria-pressed={senderRole === "customer"}
          disabled={sending || isClosed}
          onClick={() => changeRole("customer")}
        >
          Customer
        </button>

        <button
          type="button"
          className={senderRole === "agent" ? "active" : ""}
          aria-pressed={senderRole === "agent"}
          disabled={sending || isClosed}
          onClick={() => changeRole("agent")}
        >
          Agent
        </button>
      </div>

      <label htmlFor="message-content">
        {senderRole === "customer" ? "Customer message" : "Manual agent reply"}
      </label>

      <textarea
        id="message-content"
        rows={4}
        maxLength={5000}
        value={content}
        disabled={sending || isClosed}
        placeholder={
          senderRole === "customer"
            ? "Type the customer's message..."
            : "Write your reply to the customer..."
        }
        onChange={(event) => {
          setContent(event.target.value);
          setError("");
          setSuccess("");
        }}
        aria-describedby="message-character-count"
      />

      <div className="composer-footer">
        <small id="message-character-count">
          {content.length.toLocaleString()} / 5,000 characters
        </small>

        <button
          type="submit"
          className="send-button"
          disabled={sending || isClosed || !content.trim()}
        >
          {sending
            ? "Sending..."
            : `Send as ${senderRole === "customer" ? "customer" : "agent"}`}
        </button>
      </div>

      {isClosed && (
        <p role="status">This conversation is closed.</p>
      )}

      {error && (
        <p className="error" role="alert">{error}</p>
      )}

      {success && (
        <p className="success-message" role="status">{success}</p>
      )}
    </form>
  );
}