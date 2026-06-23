export async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let message = `Request failed: ${response.status}`;
    try {
      const error = await response.json();
      message = error.detail || message;
    } catch {
      // Keep the status fallback.
    }
    throw new Error(message);
  }
  return response.json();
}

export function listDecks() {
  return fetchJson("/api/decks");
}

export function getDeckSummary() {
  return fetchJson("/api/decks/summary");
}

export async function importCsv(file, deckName) {
  const form = new FormData();
  form.append("file", file);
  if (deckName) {
    form.append("deck_name", deckName);
  }
  return fetchJson("/api/import/csv", {
    method: "POST",
    body: form,
  });
}

export function startReviewSession(deckId, limit) {
  return fetchJson("/api/review-sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      deck_id: deckId ? Number(deckId) : null,
      limit: Number(limit),
    }),
  });
}

export function getNextCard(sessionId) {
  return fetchJson(`/api/review-sessions/${sessionId}/next`);
}

export function answerCard(sessionId, payload) {
  return fetchJson(`/api/review-sessions/${sessionId}/answers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
