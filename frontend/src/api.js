import { useCallback, useEffect, useState } from "react";

export async function api(path, options = {}) {
  const { body, ...rest } = options;

  let response;

  try {
    response = await fetch(`/api${path}`, {
      ...rest,
      credentials: "same-origin",
      headers: body === undefined
        ? rest.headers
        : { ...rest.headers, "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new Error(
      "Connection interrupted. Refresh to check whether your changes were saved before retrying."
    );
  }

  if (response.status === 204) return null;

  const text = await response.text();
  let data;

  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    throw new Error(`The server returned an unexpected response (${response.status}).`);
  }

  if (!response.ok) {
    const detail = data?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((item) => item.msg).join(" ")
          : detail?.message || `Request failed (${response.status}).`;

    const error = new Error(message);
    error.status = response.status;
    if (response.status === 401 && !path.startsWith("/auth/")) {
      window.dispatchEvent(new Event("auth:expired"));
    }
    throw error;
  }

  return data;
}

async function readList(path, signal) {
  const items = [];
  let offset = 0;

  while (true) {
    const separator = path.includes("?") ? "&" : "?";
    const page = await api(
      `${path}${separator}limit=100&offset=${offset}`,
      { signal }
    );

    items.push(...page);
    if (page.length < 100) return items;
    offset += 100;
  }
}

export function useLoad(path, isList = false) {
  const [version, setVersion] = useState(0);
  const [state, setState] = useState({
    key: null,
    data: null,
    error: "",
  });
  const key = `${path}:${isList}:${version}`;

  const refresh = useCallback(() => {
    setVersion((value) => value + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      try {
        const data = isList
          ? await readList(path, controller.signal)
          : await api(path, { signal: controller.signal });

        if (!controller.signal.aborted) {
          setState({ key, data, error: "" });
        }
      } catch (error) {
        if (!controller.signal.aborted) {
          setState({ key, data: null, error: error.message });
        }
      }
    }

    load();
    return () => controller.abort();
  }, [path, isList, version, key]);

  const ready = state.key === key;
  return {
    data: ready ? state.data : null,
    loading: !ready,
    error: ready ? state.error : "",
    refresh,
  };
}
