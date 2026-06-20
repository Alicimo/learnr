const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
const lerp = (a, b, t) => a + (b - a) * t;

function formatDirection(direction) {
  return direction === "reverse" ? "Reverse" : "Forward";
}

export class SwipeCardCanvas {
  constructor(canvas, { onReveal, onAnswer }) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.onReveal = onReveal;
    this.onAnswer = onAnswer;
    this.card = null;
    this.revealed = false;
    this.shownAt = null;
    this.revealedAt = null;
    this.state = {
      x: 0,
      y: 0,
      rot: 0,
      dragging: false,
      startX: 0,
      startY: 0,
      pointerId: null,
      tapCandidate: false,
      animating: false,
      width: 0,
      height: 0,
    };
    this.bindEvents();
    this.render();
  }

  setCard(card) {
    this.card = card;
    this.revealed = false;
    this.shownAt = card ? new Date() : null;
    this.revealedAt = null;
    this.resetTransform();
    this.render();
  }

  bindEvents() {
    this.canvas.addEventListener("pointerdown", (event) => this.pointerDown(event));
    this.canvas.addEventListener("pointermove", (event) => this.pointerMove(event));
    this.canvas.addEventListener("pointerup", (event) => this.pointerEnd(event));
    this.canvas.addEventListener("pointercancel", (event) => this.pointerEnd(event));
    this.canvas.addEventListener("lostpointercapture", () => this.cancelPointer());
    window.addEventListener("resize", () => this.render());
    window.addEventListener("keydown", (event) => {
      if (event.key === "ArrowLeft") {
        this.answer("left");
      }
      if (event.key === "ArrowRight") {
        this.answer("right");
      }
      if (event.key === " " || event.key === "Enter") {
        this.reveal();
      }
    });
  }

  resizeCanvas() {
    const rect = this.canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const width = Math.round(rect.width * dpr);
    const height = Math.round(rect.height * dpr);
    if (this.canvas.width !== width || this.canvas.height !== height) {
      this.canvas.width = width;
      this.canvas.height = height;
    }
    this.state.width = this.canvas.width;
    this.state.height = this.canvas.height;
  }

  threshold() {
    return this.state.width * 0.22;
  }

  resetTransform() {
    this.state.x = 0;
    this.state.y = 0;
    this.state.rot = 0;
  }

  pointerDown(event) {
    if (this.state.animating || !this.card) return;
    this.state.pointerId = event.pointerId;
    this.canvas.setPointerCapture(event.pointerId);
    this.state.startX = event.clientX;
    this.state.startY = event.clientY;
    this.state.tapCandidate = true;
    if (this.revealed) {
      this.state.dragging = true;
    }
  }

  pointerMove(event) {
    if (!this.state.dragging || this.state.animating || event.pointerId !== this.state.pointerId) return;
    const dpr = window.devicePixelRatio || 1;
    const dx = (event.clientX - this.state.startX) * dpr;
    const dy = (event.clientY - this.state.startY) * dpr;
    this.state.x = dx;
    this.state.y = dy * 0.35;
    this.state.rot = (dx / this.state.width) * 0.35;
    this.render();
  }

  pointerEnd(event) {
    if (event.pointerId !== this.state.pointerId) return;
    const dpr = window.devicePixelRatio || 1;
    const dx = (event.clientX - this.state.startX) * dpr;
    const dy = (event.clientY - this.state.startY) * dpr;
    const tapThreshold = 12 * dpr;

    if (!this.revealed && this.state.tapCandidate && Math.hypot(dx, dy) <= tapThreshold) {
      this.reveal();
    }

    if (this.state.dragging) {
      this.state.dragging = false;
      this.completeSwipeIfNeeded();
    }

    this.state.pointerId = null;
    this.state.tapCandidate = false;
  }

  cancelPointer() {
    if (this.state.dragging) {
      this.state.dragging = false;
      this.completeSwipeIfNeeded();
    }
    this.state.pointerId = null;
    this.state.tapCandidate = false;
  }

  reveal() {
    if (!this.card || this.revealed) return;
    this.revealed = true;
    this.revealedAt = new Date();
    this.onReveal?.({
      shownAt: this.shownAt,
      revealedAt: this.revealedAt,
      timeToRevealMs: this.revealedAt - this.shownAt,
    });
    this.render();
  }

  answer(direction) {
    if (!this.card || !this.revealed || this.state.animating) return;
    const offX = direction === "right" ? this.state.width * 1.2 : -this.state.width * 1.2;
    const offRot = direction === "right" ? 0.55 : -0.55;
    this.animateTo(offX, 0, offRot, () => this.finishAnswer(direction));
  }

  finishAnswer(direction) {
    const answeredAt = new Date();
    this.onAnswer?.({
      card: this.card,
      direction,
      shownAt: this.shownAt,
      revealedAt: this.revealedAt,
      answeredAt,
      timeToRevealMs: this.revealedAt ? this.revealedAt - this.shownAt : null,
      timeToGradeMs: this.revealedAt ? answeredAt - this.revealedAt : null,
    });
    this.resetTransform();
  }

  completeSwipeIfNeeded() {
    if (Math.abs(this.state.x) >= this.threshold()) {
      this.answer(this.state.x > 0 ? "right" : "left");
    } else {
      this.animateTo(0, 0, 0);
    }
  }

  animateTo(targetX, targetY, targetRot, done) {
    this.state.animating = true;
    const start = { x: this.state.x, y: this.state.y, r: this.state.rot };
    const duration = 220;
    const startTime = performance.now();
    const step = (time) => {
      const progress = clamp((time - startTime) / duration, 0, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      this.state.x = lerp(start.x, targetX, eased);
      this.state.y = lerp(start.y, targetY, eased);
      this.state.rot = lerp(start.r, targetRot, eased);
      this.render();
      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        this.state.animating = false;
        done?.();
        this.render();
      }
    };
    requestAnimationFrame(step);
  }

  roundRectPath(x, y, width, height, radius) {
    const r = Math.min(radius, width / 2, height / 2);
    const ctx = this.ctx;
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + width, y, x + width, y + height, r);
    ctx.arcTo(x + width, y + height, x, y + height, r);
    ctx.arcTo(x, y + height, x, y, r);
    ctx.arcTo(x, y, x + width, y, r);
    ctx.closePath();
  }

  drawCard() {
    const ctx = this.ctx;
    const { width, height, x, y, rot } = this.state;
    const cardWidth = width * 0.86;
    const cardHeight = height * 0.82;
    const cardX = (width - cardWidth) / 2;
    const cardY = (height - cardHeight) / 2;

    ctx.save();
    ctx.translate(width / 2 + x, height / 2 + y);
    ctx.rotate(rot);
    ctx.translate(-width / 2, -height / 2);

    ctx.save();
    ctx.globalAlpha = 0.2;
    ctx.fillStyle = "#000";
    this.roundRectPath(cardX + 8, cardY + 10, cardWidth, cardHeight, 22);
    ctx.fill();
    ctx.restore();

    ctx.fillStyle = "#fff";
    this.roundRectPath(cardX, cardY, cardWidth, cardHeight, 22);
    ctx.fill();

    ctx.strokeStyle = "rgba(0,0,0,0.08)";
    ctx.lineWidth = 2;
    this.roundRectPath(cardX, cardY, cardWidth, cardHeight, 22);
    ctx.stroke();

    ctx.fillStyle = "#62717f";
    ctx.font = `${Math.round(width * 0.035)}px system-ui, sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(formatDirection(this.card.direction), width / 2, cardY + cardHeight * 0.18);

    ctx.fillStyle = "#111827";
    ctx.font = `${Math.round(width * 0.075)}px system-ui, sans-serif`;
    ctx.fillText(this.card.prompt_text, width / 2, height / 2 - height * 0.03);

    ctx.font = `${Math.round(width * 0.047)}px system-ui, sans-serif`;
    ctx.fillStyle = "#6b7280";
    ctx.fillText(this.revealed ? this.card.answer_text : "Tap, Space, or Enter to reveal", width / 2, height / 2 + height * 0.07);

    const t = clamp(x / this.threshold(), -1, 1);
    if (Math.abs(t) > 0.05) {
      const correct = t > 0;
      ctx.save();
      ctx.globalAlpha = 0.9 * Math.min(1, Math.abs(t));
      ctx.font = `${Math.round(width * 0.07)}px system-ui, sans-serif`;
      ctx.textAlign = "left";
      ctx.textBaseline = "top";
      ctx.fillStyle = correct ? "rgba(32,160,107,0.92)" : "rgba(205,65,65,0.92)";
      ctx.strokeStyle = "rgba(255,255,255,0.92)";
      ctx.lineWidth = 6;
      const label = correct ? "CORRECT" : "WRONG";
      const labelX = cardX + cardWidth * 0.08;
      const labelY = cardY + cardHeight * 0.1;
      ctx.translate(labelX, labelY);
      ctx.rotate(correct ? -0.18 : 0.18);
      ctx.translate(-labelX, -labelY);
      ctx.strokeText(label, labelX, labelY);
      ctx.fillText(label, labelX, labelY);
      ctx.restore();
    }

    ctx.restore();
  }

  renderEmpty(message) {
    this.ctx.fillStyle = "#65717c";
    this.ctx.font = `${Math.round(this.state.width * 0.045)}px system-ui, sans-serif`;
    this.ctx.textAlign = "center";
    this.ctx.textBaseline = "middle";
    this.ctx.fillText(message, this.state.width / 2, this.state.height / 2);
  }

  render() {
    this.resizeCanvas();
    this.ctx.clearRect(0, 0, this.state.width, this.state.height);
    if (!this.card) {
      this.renderEmpty("No card loaded");
      return;
    }
    this.drawCard();
  }
}
