import { answerCard, importCsv, listDecks, startReviewSession } from "./api.js";
import { SwipeCardCanvas } from "./swipe-card.js";

const deckSelect = document.querySelector("#deckSelect");
const sessionLimit = document.querySelector("#sessionLimit");
const startSessionButton = document.querySelector("#startSession");
const importForm = document.querySelector("#importForm");
const csvFile = document.querySelector("#csvFile");
const deckName = document.querySelector("#deckName");
const sessionLabel = document.querySelector("#sessionLabel");
const progressText = document.querySelector("#progressText");
const statusText = document.querySelector("#statusText");
const progressBar = document.querySelector("#progressBar");
const directionText = document.querySelector("#directionText");
const reviewCountText = document.querySelector("#reviewCountText");
const tagsText = document.querySelector("#tagsText");

const state = {
  session: null,
  currentCard: null,
  sessionCards: [],
  cardById: new Map(),
  queue: [],
  progress: new Map(),
};

const canvas = new SwipeCardCanvas(document.querySelector("#swipeCanvas"), {
  onAnswer: async (answer) => {
    await submitAnswer(answer);
  },
});

function iso(date) {
  return date ? date.toISOString() : null;
}

function setStatus(message) {
  statusText.textContent = message;
}

function setMode(mode) {
  document.body.dataset.mode = mode;
}

function renderProgressSegments() {
  progressBar.innerHTML = "";
  for (const card of state.sessionCards) {
    const segment = document.createElement("span");
    segment.className = `progress-segment ${state.progress.get(card.id) || "pending"}`;
    progressBar.append(segment);
  }
}

function updateProgress(session) {
  const target = session?.target_count || 0;
  const completed = [...state.progress.values()].filter((status) => status === "passed").length;
  progressText.textContent = `${completed} / ${target}`;
  renderProgressSegments();
  sessionLabel.textContent = session ? `Session ${session.id}` : "No session";
}

function updateCardDetails(card) {
  if (!card) {
    directionText.textContent = "-";
    reviewCountText.textContent = "-";
    tagsText.textContent = "-";
    return;
  }
  directionText.textContent = card.direction === "reverse" ? "Reverse" : "Forward";
  reviewCountText.textContent = String(card.review_count);
  tagsText.textContent = card.tags.length ? card.tags.join(", ") : "-";
}

async function refreshDecks() {
  const decks = await listDecks();
  deckSelect.innerHTML = "";
  const allOption = document.createElement("option");
  allOption.value = "";
  allOption.textContent = "All due cards";
  deckSelect.append(allOption);
  for (const deck of decks) {
    const option = document.createElement("option");
    option.value = deck.id;
    option.textContent = deck.name;
    deckSelect.append(option);
  }
}

function setCurrentCard(card) {
  state.currentCard = card;
  updateCardDetails(card);
  canvas.setCard(card);
}

function showNextQueuedCard() {
  const card = state.cardById.get(state.queue[0]) || null;
  setCurrentCard(card);
  updateProgress(state.session);
  if (!card) {
    setMode("setup");
    setStatus(state.session?.target_count ? "Session complete." : "No due cards.");
    return;
  }
  setMode("reviewing");
  setStatus(`${state.queue.length} card${state.queue.length === 1 ? "" : "s"} remaining.`);
}

function loadSessionPayload(payload) {
  const cards = payload.cards?.length ? payload.cards : payload.card ? [payload.card] : [];
  state.session = payload.session;
  state.sessionCards = cards;
  state.cardById = new Map(cards.map((card) => [card.id, card]));
  state.queue = cards.map((card) => card.id);
  state.progress = new Map(cards.map((card) => [card.id, "pending"]));
  showNextQueuedCard();
}

async function submitAnswer(answer) {
  if (!state.session || !answer.card) return;
  try {
    const result = await answerCard(state.session.id, {
      card_id: answer.card.id,
      direction: answer.direction,
      shown_at: iso(answer.shownAt),
      revealed_at: iso(answer.revealedAt),
      answered_at: iso(answer.answeredAt),
      time_to_reveal_ms: answer.timeToRevealMs,
      time_to_grade_ms: answer.timeToGradeMs,
    });
    state.session = result.session;
    const cardId = answer.card.id;
    state.queue = state.queue.filter((queuedCardId) => queuedCardId !== cardId);
    if (result.correct) {
      state.progress.set(cardId, "passed");
    } else {
      state.progress.set(cardId, "failed");
      state.queue.push(cardId);
    }
    showNextQueuedCard();
  } catch (error) {
    setStatus(error.message);
  }
}

startSessionButton.addEventListener("click", async () => {
  try {
    setStatus("Starting session...");
    const payload = await startReviewSession(deckSelect.value, sessionLimit.value);
    loadSessionPayload(payload);
  } catch (error) {
    setStatus(error.message);
  }
});

importForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!csvFile.files.length) {
    setStatus("Choose a CSV file first.");
    return;
  }
  try {
    setStatus("Importing...");
    const summary = await importCsv(csvFile.files[0], deckName.value.trim());
    await refreshDecks();
    setStatus(`Imported ${summary.rows_read} rows, created ${summary.cards_created} cards.`);
    csvFile.value = "";
  } catch (error) {
    setStatus(error.message);
  }
});

setMode("setup");
await refreshDecks();
updateProgress(null);
updateCardDetails(null);
