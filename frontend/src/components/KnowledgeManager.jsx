import { useRef, useState } from "react";
import { api, useLoad } from "../api";

const emptyPolicy = {
  category: "return",
  title: "",
  content: "",
};

export default function KnowledgeManager({ brand }) {
  const path = `/brands/${brand.id}/knowledge`;
  const policies = useLoad(path, true);

  const [editingId, setEditingId] = useState("");
  const [form, setForm] = useState({ ...emptyPolicy });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const lock = useRef(false);

  function resetForm() {
    setEditingId("");
    setForm({ ...emptyPolicy });
  }

  function edit(policy) {
    setEditingId(policy.id);
    setForm({
      category: policy.category,
      title: policy.title,
      content: policy.content,
    });
    setError("");
    setNotice("");
  }

  async function save(event) {
    event.preventDefault();
    if (lock.current) return;

    if (!form.title.trim() || !form.content.trim()) {
      setError("Title and content cannot be blank.");
      return;
    }

    lock.current = true;
    setBusy(true);
    setError("");
    setNotice("");

    try {
      await api(editingId ? `${path}/${editingId}` : path, {
        method: editingId ? "PUT" : "POST",
        body: {
          category: form.category,
          title: form.title.trim(),
          content: form.content.trim(),
        },
      });

      setNotice(editingId ? "Policy updated." : "Policy created.");
      resetForm();
      policies.refresh();
    } catch (error) {
      setError(error.message);
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }

  async function remove(policy) {
    if (lock.current) return;
    if (!window.confirm(`Delete "${policy.title}" from ${brand.name}?`)) return;

    lock.current = true;
    setBusy(true);
    setError("");
    setNotice("");

    try {
      await api(`${path}/${policy.id}`, { method: "DELETE" });
      if (editingId === policy.id) resetForm();
      setNotice("Policy deleted.");
      policies.refresh();
    } catch (error) {
      setError(error.message);
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }

  function updateField(event) {
    setForm((previous) => ({
      ...previous,
      [event.target.name]: event.target.value,
    }));
  }

  return (
    <section className="panel">
      <div className="heading-row">
        <h2>{brand.name} policies</h2>
        <button onClick={policies.refresh} disabled={busy || policies.loading}>
          Refresh policies
        </button>
      </div>

      <p className="muted">
        Changes apply to this brand. Generate a new draft to use updated policies;
        existing draft snapshots keep their original context.
      </p>

      {error && <p className="error" role="alert">{error}</p>}
      {notice && <p className="success" role="status">{notice}</p>}

      <form className="subpanel" onSubmit={save}>
        <h3>{editingId ? "Edit policy" : "Create policy"}</h3>

        <fieldset disabled={busy || policies.loading}>
          <label>
            Category
            <select name="category" value={form.category} onChange={updateField}>
              <option value="return">Return</option>
              <option value="refund">Refund</option>
              <option value="shipping">Shipping</option>
              <option value="cancellation">Cancellation</option>
            </select>
          </label>

          <label>
            Title
            <input
              name="title"
              value={form.title}
              onChange={updateField}
              maxLength={200}
              required
            />
          </label>

          <label>
            Policy content
            <textarea
              name="content"
              value={form.content}
              onChange={updateField}
              rows={6}
              maxLength={20000}
              required
            />
          </label>

          <div className="actions">
            <button
              className="primary"
              disabled={!form.title.trim() || !form.content.trim()}
            >
              {busy ? "Saving..." : editingId ? "Save policy" : "Create policy"}
            </button>

            {editingId && (
              <button type="button" onClick={resetForm}>Cancel editing</button>
            )}
          </div>
        </fieldset>
      </form>

      {policies.loading && <p role="status">Loading policies...</p>}
      {policies.error && <p className="error" role="alert">{policies.error}</p>}

      {!policies.loading && !policies.error && (
        policies.data.length ? policies.data.map((policy) => (
          <article className="policy-card" key={policy.id}>
            <p className="eyebrow">{policy.category}</p>
            <h3>{policy.title}</h3>
            <p className="preserve">{policy.content}</p>
            <div className="actions">
              <button onClick={() => edit(policy)} disabled={busy}>Edit</button>
              <button
                className="danger"
                onClick={() => remove(policy)}
                disabled={busy}
              >
                Delete
              </button>
            </div>
          </article>
        )) : (
          <p>No policies yet. Create the first policy above.</p>
        )
      )}
    </section>
  );
}