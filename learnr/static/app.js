import { answerCard, getDeckSummary, importCsv, startReviewSession } from "./api.js";
import { SwipeCardCanvas } from "./swipe-card.js";

const sessionLimit = document.querySelector("#sessionLimit");
const dashboardStatus = document.querySelector("#dashboardStatus");
const totalDueReviews = document.querySelector("#totalDueReviews");
const totalNewCards = document.querySelector("#totalNewCards");
const totalCards = document.querySelector("#totalCards");
const deckList = document.querySelector("#deckList");
const startAllSessionButton = document.querySelector("#startAllSession");
const openImportDialogButton = document.querySelector("#openImportDialog");
const importDialog = document.querySelector("#importDialog");
const importForm = document.querySelector("#importForm");
const csvFile = document.querySelector("#csvFile");
const deckName = document.querySelector("#deckName");
const importError = document.querySelector("#importError");
const closeImportDialogButton = document.querySelector("#closeImportDialog");
const cancelImportButton = document.querySelector("#cancelImport");
const confirmImportButton = document.querySelector("#confirmImport");
const progressText = document.querySelector("#progressText");
const statusText = document.querySelector("#statusText");
const progressBar = document.querySelector("#progressBar");
const directionText = document.querySelector("#directionText");
const reviewCountText = document.querySelector("#reviewCountText");
const tagsText = document.querySelector("#tagsText");
const readyCardCount = document.querySelector("#readyCardCount");
const sessionReadyCard = document.querySelector("#sessionReadyCard");

const state = {
  session: null,
  currentCard: null,
  sessionCards: [],
  cardById: new Map(),
  queue: [],
  progress: new Map(),
  deckSummary: null,
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

function setDashboardStatus(message) {
  dashboardStatus.textContent = message;
}

function setMode(mode) {
  document.body.dataset.mode = mode;
}

function setImportError(message) {
  importError.textContent = message;
  importError.hidden = !message;
}

function setImportLoading(isLoading) {
  confirmImportButton.disabled = isLoading;
  closeImportDialogButton.disabled = isLoading;
  cancelImportButton.disabled = isLoading;
  confirmImportButton.textContent = isLoading ? "Importing..." : "Import deck";
}

function openImportDialog() {
  if (importDialog.open) return;
  setImportError("");
  setImportLoading(false);
  importDialog.showModal();
  csvFile.focus();
}

function closeImportDialog() {
  if (!importDialog.open) return;
  importDialog.close();
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

function pluralize(count, singular, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`;
}

function updateReadyCardCount(count) {
  readyCardCount.textContent = pluralize(count, "card");
}

function reviewedPercent(summary) {
  if (!summary.total_cards) return 0;
  return (summary.reviewed_cards / summary.total_cards) * 100;
}

function reviewedLabel(summary) {
  const percent = reviewedPercent(summary);
  if (!percent) return "0% reviewed";
  if (percent < 1) return `${summary.reviewed_cards} reviewed (<1%)`;
  return `${Math.round(percent)}% reviewed`;
}

function actionLabel(summary) {
  if (summary.due_review_cards) {
    return "Start Review";
  }
  if (summary.new_cards) {
    return "Study New Cards";
  }
  return "No Cards Due";
}

function dueBreakdown(summary) {
  if (!summary.due_review_cards) {
    return "No review cards due right now.";
  }
  return `${pluralize(summary.due_forward_cards, "forward")} · ${pluralize(summary.due_reverse_cards, "reverse")}`;
}

function renderDeckCard(summary) {
  const article = document.createElement("article");
  article.className = "deck-card";

  const title = document.createElement("h3");
  title.textContent = summary.name;

  const stats = document.createElement("p");
  stats.className = "deck-stats";
  stats.textContent = `${pluralize(summary.total_cards, "card")} · ${pluralize(summary.due_review_cards, "due review")} · ${pluralize(summary.new_cards, "new card")} · ${reviewedLabel(summary)}`;

  const meter = document.createElement("div");
  meter.className = "deck-meter";
  meter.setAttribute("aria-label", `${summary.due_review_cards} due reviews`);
  const meterFill = document.createElement("span");
  const dueRatio = summary.total_cards ? summary.due_review_cards / summary.total_cards : 0;
  meterFill.style.width = `${Math.min(100, Math.round(dueRatio * 100))}%`;
  meter.append(meterFill);

  const breakdown = document.createElement("p");
  breakdown.className = "deck-breakdown";
  breakdown.textContent = dueBreakdown(summary);

  const startButton = document.createElement("button");
  startButton.type = "button";
  startButton.textContent = actionLabel(summary);
  startButton.disabled = !summary.due_review_cards && !summary.new_cards;
  startButton.addEventListener("click", async () => {
    await startReview(summary.id);
  });

  const details = document.createElement("div");
  details.className = "deck-card-details";
  details.append(title, stats, meter, breakdown);
  article.append(details, startButton);
  return article;
}

function renderDashboard(summary) {
  state.deckSummary = summary;
  totalDueReviews.textContent = String(summary.total.due_review_cards);
  totalNewCards.textContent = String(summary.total.new_cards);
  totalCards.textContent = String(summary.total.total_cards);
  startAllSessionButton.disabled = !summary.total.due_review_cards && !summary.total.new_cards;
  startAllSessionButton.textContent = actionLabel(summary.total);
  setDashboardStatus(
    summary.total.total_cards
      ? `${pluralize(summary.total.due_review_cards, "due review")} across ${pluralize(summary.decks.length, "deck")}.`
      : "Import cards to begin.",
  );

  deckList.innerHTML = "";
  if (!summary.decks.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "No decks yet. Import a CSV deck to start studying.";
    deckList.append(empty);
    return;
  }
  for (const deck of summary.decks) {
    deckList.append(renderDeckCard(deck));
  }
}

async function refreshDashboard() {
  setDashboardStatus("Loading deck summary...");
  const summary = await getDeckSummary();
  renderDashboard(summary);
}

function setCurrentCard(card) {
  state.currentCard = card;
  updateCardDetails(card);
  canvas.setCard(card);
}

function showNextQueuedCard() {
  const card = state.cardById.get(state.queue[0]) || null;
  if (card) {
    setMode("reviewing");
  }
  setCurrentCard(card);
  updateProgress(state.session);
  if (!card) {
    setMode("setup");
    setStatus(state.session?.target_count ? "Session complete." : "No due cards.");
    return;
  }
  setStatus(`${state.queue.length} card${state.queue.length === 1 ? "" : "s"} remaining.`);
}

function loadSessionPayload(payload) {
  const cards = payload.cards?.length ? payload.cards : payload.card ? [payload.card] : [];
  state.session = payload.session;
  state.sessionCards = cards;
  state.cardById = new Map(cards.map((card) => [card.id, card]));
  state.queue = cards.map((card) => card.id);
  state.progress = new Map(cards.map((card) => [card.id, "pending"]));
  setCurrentCard(null);
  updateProgress(state.session);
  if (!cards.length) {
    setMode("setup");
    setStatus("No due cards.");
    return;
  }
  updateReadyCardCount(cards.length);
  setMode("ready");
  setStatus("Ready when you are.");
  sessionReadyCard.focus();
}

function beginQueuedCards() {
  if (!state.session || !state.queue.length) return;
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
    if (!state.currentCard) {
      await refreshDashboard();
    }
  } catch (error) {
    setStatus(error.message);
  }
}

async function startReview(deckId) {
  try {
    setStatus("Starting session...");
    const payload = await startReviewSession(deckId, sessionLimit.value);
    loadSessionPayload(payload);
  } catch (error) {
    setStatus(error.message);
  }
}

startAllSessionButton.addEventListener("click", async () => {
  await startReview(null);
});

sessionReadyCard.addEventListener("click", () => {
  beginQueuedCards();
});

sessionReadyCard.addEventListener("keydown", (event) => {
  if (event.key !== " " && event.key !== "Enter") return;
  event.preventDefault();
  beginQueuedCards();
});

openImportDialogButton.addEventListener("click", () => {
  openImportDialog();
});

closeImportDialogButton.addEventListener("click", () => {
  closeImportDialog();
});

cancelImportButton.addEventListener("click", () => {
  closeImportDialog();
});

importDialog.addEventListener("click", (event) => {
  if (event.target === importDialog && !confirmImportButton.disabled) {
    closeImportDialog();
  }
});

importDialog.addEventListener("cancel", (event) => {
  if (confirmImportButton.disabled) {
    event.preventDefault();
  }
});

importForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!csvFile.files.length) {
    setImportError("Choose a CSV file first.");
    csvFile.focus();
    return;
  }
  try {
    setImportError("");
    setImportLoading(true);
    setStatus("Importing...");
    const summary = await importCsv(csvFile.files[0], deckName.value.trim());
    await refreshDashboard();
    setStatus(`Imported ${summary.rows_read} rows, created ${summary.cards_created} cards.`);
    csvFile.value = "";
    closeImportDialog();
  } catch (error) {
    setImportError(error.message);
  } finally {
    setImportLoading(false);
  }
});

setMode("setup");
await refreshDashboard();
updateProgress(null);
updateCardDetails(null);
setImportError("");
