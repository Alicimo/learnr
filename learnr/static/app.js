import { answerCard, getNextCard, importCsv, listDecks, startReviewSession } from "./api.js";
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

function updateProgress(session) {
  const target = session?.target_count || 0;
  const completed = session?.completed_count || 0;
  progressText.textContent = `${completed} / ${target}`;
  progressBar.style.width = target ? `${Math.round((completed / target) * 100)}%` : "0";
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

function loadSessionPayload(payload) {
  state.session = payload.session;
  state.currentCard = payload.card;
  updateProgress(payload.session);
  updateCardDetails(payload.card);
  canvas.setCard(payload.card);
  if (!payload.card) {
    setStatus(payload.session.target_count ? "Session complete." : "No due cards.");
  } else {
    setStatus(`${payload.remaining} card${payload.remaining === 1 ? "" : "s"} remaining.`);
  }
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
    updateProgress(result.session);
    const next = await getNextCard(state.session.id);
    loadSessionPayload(next);
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

await refreshDecks();
updateProgress(null);
updateCardDetails(null);
