const $ = (id) => document.getElementById(id);

const ui = {
  status: $("connectionStatus"),
  dropZone: $("dropZone"),
  dropLabel: $("dropLabel"),
  fileInput: $("fileInput"),
  fileChip: $("fileChip"),
  fileName: $("fileName"),
  removeFile: $("removeFileBtn"),
  generate: $("generateBtn"),
  demo: $("demoBtn"),
  heroDemo: $("heroDemoBtn"),
  source: $("sourceText"),
  count: $("characterCount"),
  processing: $("processing"),
  processingTitle: $("processingTitle"),
  processingPercent: $("processingPercent"),
  processingBar: $("processingBar"),
  error: $("errorPanel"),
  errorMessage: $("errorMessage"),
  lesson: $("lesson"),
  lessonTitle: $("lessonTitle"),
  lessonMeta: $("lessonMeta"),
  lessonProgress: $("lessonProgress"),
  narrationTitle: $("narrationTitle"),
  narration: $("narrationContent"),
  takeaways: $("takeawayList"),
  takeawayCount: $("takeawayCount"),
  sourceContent: $("sourceContent"),
  engine: $("engineBadge"),
  play: $("playBtn"),
  playIcon: $("playIcon"),
  playLabel: $("playLabel"),
  restart: $("restartBtn"),
  stop: $("stopBtn"),
  voice: $("voiceSelect"),
  speed: $("speedRange"),
  speedValue: $("speedValue"),
  progress: $("timelineProgress"),
  elapsed: $("elapsedTime"),
  total: $("totalTime"),
  copy: $("copyBtn"),
  download: $("downloadBtn"),
  newLesson: $("newLessonBtn"),
  replayKey: $("replayKeyBtn"),
  memory: $("memoryText"),
  studySummary: $("studySummary"),
  quizList: $("quizList"),
  flashcardList: $("flashcardList"),
  nextStepsList: $("nextStepsList"),
  deckMapTitle: $("deckMapTitle"),
  deckMapMeta: $("deckMapMeta"),
  deckCount: $("deckCount"),
  deckMapList: $("deckMapList"),
  quizScore: $("quizScore"),
  tutorForm: $("tutorForm"),
  tutorQuestion: $("tutorQuestion"),
  tutorAnswer: $("tutorAnswer"),
  history: $("history"),
  historyList: $("historyList"),
  clearHistory: $("clearHistoryBtn"),
  toast: $("toast"),
};

let file = null;
let lesson = null;
let mode = "explainer";
let utterance = null;
let timer = null;
let quizState = { answered: [], correct: 0 };

function setStatus(online, label) {
  ui.status.innerHTML = `<span class="status-dot ${online ? "online" : "offline"}"></span><span>${label}</span>`;
}

async function requestJson(url, options) {
  const response = await fetch(url, options);
  const text = await response.text();

  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch (error) {
    if (!response.ok) {
      throw new Error("The backend is not responding. Start the Flask app with python app.py and open http://localhost:5000");
    }
    throw new Error("The server returned an unexpected response. Please check the backend and try again.");
  }

  if (!response.ok || data.error) {
    throw new Error(data.error || "The request could not be completed.");
  }

  return data;
}

async function checkHealth() {
  try {
    const response = await fetch("/api/health");
    const data = await response.json();
    setStatus(response.ok, data.ai_configured ? `AI ready · ${data.ai_model}` : "Offline mode · add AI key");
  } catch (error) {
    setStatus(false, "Offline demo ready");
  }
}

function showError(message) {
  ui.errorMessage.textContent = message;
  ui.error.classList.remove("hidden");
}

function hideError() { ui.error.classList.add("hidden"); }

function updateForm() {
  ui.count.textContent = `${ui.source.value.length.toLocaleString()} / 24,000`;
  ui.generate.disabled = !(file || ui.source.value.trim());
}

function chooseFile(selected) {
  const valid = ["application/pdf", "image/jpeg", "image/png", "image/webp"];
  if (!valid.includes(selected.type)) return showError("Choose a PDF, JPG, PNG, or WEBP file.");
  if (selected.size > 4 * 1024 * 1024) return showError("That file is over 4 MB. Choose a smaller slide deck.");
  file = selected;
  ui.fileName.textContent = selected.name;
  ui.fileChip.classList.remove("hidden");
  ui.dropLabel.textContent = "Slide selected";
  hideError();
  updateForm();
}

function resetFile() {
  file = null;
  ui.fileInput.value = "";
  ui.fileChip.classList.add("hidden");
  ui.dropLabel.textContent = "Drop your slide here";
  updateForm();
}

function progress(percent, title, step) {
  ui.processingPercent.textContent = `${percent}%`;
  ui.processingBar.style.width = `${percent}%`;
  ui.processingTitle.textContent = title;
  for (let index = 1; index <= 4; index += 1) $("processStep" + index).classList.toggle("active", index <= step);
}

function wait(milliseconds) { return new Promise((resolve) => setTimeout(resolve, milliseconds)); }

async function createLesson(useDemo = false) {
  hideError();
  ui.processing.classList.remove("hidden");
  ui.lesson.classList.add("hidden");
  progress(12, "Preparing your session", 1);
  try {
    let extracted;
    if (useDemo) {
      extracted = await requestJson("/api/demo");
    } else if (file) {
      const body = new FormData();
      body.append("file", file);
      extracted = await requestJson("/api/extract", { method: "POST", body });
    } else if (ui.source.value.trim()) {
      extracted = { extracted_text: ui.source.value.trim(), slides: [{ number: 1, title: "Pasted lesson", text: ui.source.value.trim() }], meta: { source: "pasted text", pages: 1 } };
    } else {
      throw new Error("Add a slide or paste some source text first.");
    }
    progress(55, "Finding the key ideas", 2);
    await wait(250);
    const result = useDemo ? extracted : await requestJson("/api/narrate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: extracted.extracted_text, mode }),
    });
    lesson = { ...result, extracted_text: extracted.extracted_text, slides: extracted.slides || [{ number: 1, title: result.title, text: extracted.extracted_text }], meta: result.meta || extracted.meta };
    if (!useDemo) {
      const kitResult = await requestJson("/api/study-kit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: extracted.extracted_text }),
      });
      lesson.study_kit = kitResult.study_kit;
      lesson.study_kit_engine = kitResult.meta?.engine;
    } else {
      lesson.study_kit = buildOfflineStudyKit(extracted);
      lesson.study_kit_engine = "Demo study coach";
    }
    progress(84, "Building your listening guide", 3);
    await wait(350);
    renderLesson();
    progress(100, "Your lesson is ready", 4);
    await wait(250);
    ui.processing.classList.add("hidden");
    ui.lesson.classList.remove("hidden");
    ui.lesson.focus();
  } catch (error) {
    ui.processing.classList.add("hidden");
    showError(error.message);
  }
}

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[character]));
}

function estimateSeconds(text) { return Math.max(1, Math.round(text.trim().split(/\s+/).length / 2.2)); }
function formatTime(seconds) { return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`; }

function renderLesson() {
  const title = lesson.title || "Your lecture";
  lesson.workspace = lesson.workspace || { activeParagraph: 0, completedParagraphs: [] };
  ui.lessonTitle.textContent = `${title} is ready`;
  ui.narrationTitle.textContent = title;
  ui.lessonMeta.textContent = `${lesson.meta?.engine || "Smart offline guide"} · ${lesson.meta?.pages || 1} page · ${lesson.meta?.characters || lesson.extracted_text.length} characters`;
  ui.engine.textContent = lesson.meta?.engine || "AI guided";
  ui.narration.innerHTML = getParagraphs(lesson.narration).map((paragraph, index) => `<p class="narration-paragraph ${index === lesson.workspace.activeParagraph ? "current" : ""} ${lesson.workspace.completedParagraphs.includes(index) ? "completed" : ""}" data-paragraph-index="${index}" role="button" tabindex="0" aria-label="Play paragraph ${index + 1}"><span class="paragraph-marker">${String(index + 1).padStart(2, "0")}</span><span>${escapeHtml(paragraph)}</span></p>`).join("");
  ui.takeaways.innerHTML = (lesson.key_points || []).map((point) => `<li>${escapeHtml(point)}</li>`).join("");
  ui.takeawayCount.textContent = lesson.key_points?.length || 0;
  ui.sourceContent.textContent = lesson.extracted_text;
  ui.memory.textContent = lesson.key_points?.[0] || "Replay the lesson once, then explain the main idea in your own words.";
  renderStudyKit();
  renderDeckMap();
  updateLessonProgress();
  saveLessonHistory();
  ui.total.textContent = formatTime(estimateSeconds(lesson.narration));
}

function getParagraphs(text) { return text.split(/\n\s*\n/).map((paragraph) => paragraph.trim()).filter(Boolean); }

function updateLessonProgress() {
  const total = getParagraphs(lesson.narration).length;
  const completed = lesson.workspace.completedParagraphs.length;
  const percent = total ? Math.round((completed / total) * 100) : 0;
  ui.lessonProgress.textContent = `${percent}% complete`;
  ui.narration.querySelectorAll(".narration-paragraph").forEach((paragraph) => {
    const index = Number(paragraph.dataset.paragraphIndex);
    paragraph.classList.toggle("current", index === lesson.workspace.activeParagraph);
    paragraph.classList.toggle("completed", lesson.workspace.completedParagraphs.includes(index));
  });
}

function persistWorkspace() {
  const entries = readHistory();
  const index = entries.findIndex((entry) => entry.title === lesson.title);
  if (index < 0) return;
  entries[index] = { ...entries[index], workspace: lesson.workspace, savedAt: new Date().toISOString() };
  try { localStorage.setItem("lectureLensHistory", JSON.stringify(entries)); } catch (error) { return; }
  renderHistory();
}

function readHistory() {
  try { return JSON.parse(localStorage.getItem("lectureLensHistory") || "[]"); } catch (error) { return []; }
}

function saveLessonHistory() {
  const entries = readHistory().filter((entry) => entry.title !== lesson.title);
  entries.unshift({ ...lesson, savedAt: new Date().toISOString() });
  try { localStorage.setItem("lectureLensHistory", JSON.stringify(entries.slice(0, 6))); } catch (error) { return; }
  renderHistory();
}

function renderHistory() {
  const entries = readHistory();
  ui.history.classList.toggle("hidden", entries.length === 0);
  ui.historyList.innerHTML = entries.map((entry, index) => { const total = getParagraphs(entry.narration || "").length; const completed = entry.workspace?.completedParagraphs?.length || 0; const percent = total ? Math.round((completed / total) * 100) : 0; return `<button class="history-item" data-history-index="${index}" type="button"><span class="history-icon">${String(index + 1).padStart(2, "0")}</span><span><strong>${escapeHtml(entry.title || "Untitled lesson")}</strong><small>${percent}% complete · ${escapeHtml(entry.meta?.mode || "explainer")} · ${new Date(entry.savedAt).toLocaleDateString()}</small></span><span aria-hidden="true">&#8594;</span></button>`; }).join("");
}

function restoreHistory(index) {
  const entry = readHistory()[index];
  if (!entry) return;
  stopSpeech();
  lesson = entry;
  renderLesson();
  ui.lesson.classList.remove("hidden");
  ui.lesson.scrollIntoView({ behavior: "smooth", block: "start" });
}

function buildOfflineStudyKit(source) {
  const points = source.key_points || ["Replay the lesson and identify its main idea."];
  return {
    summary: points.join(" "),
    quiz: [{ question: "What is the main idea of this lesson?", answer: points[0], explanation: "Start with the first key point, then add one supporting detail." }],
    flashcards: points.map((point) => ({ front: point, back: "Explain this idea in your own words." })),
    next_steps: ["Replay the narration once.", "Explain the key idea without looking at the source.", "Return later and answer the quiz aloud."],
  };
}

function renderStudyKit() {
  const kit = lesson.study_kit || buildOfflineStudyKit(lesson);
  ui.studySummary.textContent = kit.summary || "Review the narration, then test yourself from memory.";
  quizState = { answered: [], correct: 0 };
  ui.quizList.innerHTML = (kit.quiz || []).map((item, index) => `<div class="quiz-item" data-quiz-index="${index}"><p class="quiz-question"><strong>${index + 1}.</strong> ${escapeHtml(item.question)}</p><div class="quiz-answer-row"><input class="quiz-answer" maxlength="240" placeholder="Write your answer"><button class="subtle-button check-answer" type="button">Check</button></div><div class="quiz-feedback hidden"></div><div class="quiz-reveal"><strong>Model answer:</strong> ${escapeHtml(item.answer)}<br>${escapeHtml(item.explanation)}</div></div>`).join("");
  ui.quizScore.textContent = `0 / ${(kit.quiz || []).length}`;
  ui.flashcardList.innerHTML = (kit.flashcards || []).map((card) => `<details class="flashcard"><summary>${escapeHtml(card.front)}</summary><p>${escapeHtml(card.back)}</p></details>`).join("");
  ui.nextStepsList.innerHTML = (kit.next_steps || []).map((step) => `<li>${escapeHtml(step)}</li>`).join("");
  ui.tutorAnswer.classList.add("hidden");
  ui.tutorAnswer.textContent = "";
}

function renderDeckMap() {
  const slides = lesson.slides || [{ number: 1, title: lesson.title || "Your lesson", text: lesson.extracted_text }];
  ui.deckMapTitle.textContent = `${lesson.title || "Your lesson"} map`;
  ui.deckMapMeta.textContent = `${slides.length} structured ${slides.length === 1 ? "slide" : "slides"} ready for focused review.`;
  ui.deckCount.textContent = `${slides.length} ${slides.length === 1 ? "slide" : "slides"}`;
  ui.deckMapList.innerHTML = slides.map((slide, index) => `<button class="deck-slide ${index === 0 ? "selected" : ""}" data-slide-index="${index}" type="button"><span class="deck-slide-number">${String(slide.number || index + 1).padStart(2, "0")}</span><span class="deck-slide-body"><strong>${escapeHtml(slide.title || `Slide ${index + 1}`)}</strong><small>${escapeHtml((slide.text || "").replace(/\s+/g, " ").slice(0, 140))}${(slide.text || "").length > 140 ? "..." : ""}</small></span><span class="deck-slide-action" aria-hidden="true">&#9654;</span></button>`).join("");
}

function checkQuizAnswer(item) {
  const index = Number(item.dataset.quizIndex);
  const kit = lesson.study_kit || buildOfflineStudyKit(lesson);
  const question = kit.quiz?.[index];
  const input = item.querySelector(".quiz-answer");
  const feedback = item.querySelector(".quiz-feedback");
  if (!question || !input.value.trim()) return;
  const answerWords = question.answer.toLowerCase().split(/\W+/).filter((word) => word.length > 4);
  const response = input.value.toLowerCase();
  const correct = answerWords.some((word) => response.includes(word));
  if (!quizState.answered.includes(index)) {
    quizState.answered.push(index);
    if (correct) quizState.correct += 1;
  }
  feedback.className = `quiz-feedback ${correct ? "correct" : "needs-review"}`;
  feedback.textContent = correct ? "Nice. You captured the central idea." : "Keep going. Compare your answer with the model answer below.";
  ui.quizScore.textContent = `${quizState.correct} / ${kit.quiz.length}`;
}

async function askTutor(event) {
  event.preventDefault();
  const question = ui.tutorQuestion.value.trim();
  if (!question || !lesson) return;
  const button = ui.tutorForm.querySelector("button");
  button.disabled = true;
  button.textContent = "Thinking...";
  ui.tutorAnswer.classList.remove("hidden");
  ui.tutorAnswer.textContent = "The tutor is reading this lesson...";
  try {
    const result = await requestJson("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: lesson.extracted_text, question }) });
    ui.tutorAnswer.textContent = `${result.answer} (${result.meta?.engine || "lesson tutor"})`;
  } catch (error) {
    ui.tutorAnswer.textContent = error.message;
  } finally {
    button.disabled = false;
    button.textContent = "Ask tutor";
  }
}

function stopSpeech() {
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
  clearInterval(timer);
  ui.playIcon.textContent = "▶";
  ui.playLabel.textContent = "Play lesson";
  ui.progress.style.width = "0%";
  ui.elapsed.textContent = "0:00";
}

function speak(text = lesson?.narration) {
  if (!text || !("speechSynthesis" in window)) return showError("Browser audio is unavailable. Try Chrome or Edge for voice playback.");
  stopSpeech();
  const paragraphIndex = arguments.length > 1 ? arguments[1] : null;
  if (paragraphIndex !== null) {
    lesson.workspace.activeParagraph = paragraphIndex;
    updateLessonProgress();
    persistWorkspace();
  }
  utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = Number(ui.speed.value);
  utterance.voice = window.speechSynthesis.getVoices().find((voiceOption) => voiceOption.name === ui.voice.value) || null;
  utterance.onstart = () => {
    const total = estimateSeconds(text);
    const started = Date.now();
    ui.playIcon.textContent = "Ⅱ";
    ui.playLabel.textContent = "Pause lesson";
    timer = setInterval(() => {
      const elapsed = Math.min(total, Math.round((Date.now() - started) / 1000));
      ui.elapsed.textContent = formatTime(elapsed);
      ui.progress.style.width = `${(elapsed / total) * 100}%`;
    }, 250);
  };
  utterance.onend = () => {
    if (paragraphIndex !== null) {
      if (!lesson.workspace.completedParagraphs.includes(paragraphIndex)) lesson.workspace.completedParagraphs.push(paragraphIndex);
      lesson.workspace.activeParagraph = Math.min(paragraphIndex + 1, getParagraphs(lesson.narration).length - 1);
      updateLessonProgress();
      persistWorkspace();
    }
    stopSpeech();
  };
  window.speechSynthesis.speak(utterance);
}

ui.dropZone.addEventListener("click", () => ui.fileInput.click());
ui.fileInput.addEventListener("change", () => ui.fileInput.files[0] && chooseFile(ui.fileInput.files[0]));
ui.dropZone.addEventListener("dragover", (event) => { event.preventDefault(); ui.dropZone.classList.add("drag-over"); });
ui.dropZone.addEventListener("dragleave", () => ui.dropZone.classList.remove("drag-over"));
ui.dropZone.addEventListener("drop", (event) => { event.preventDefault(); ui.dropZone.classList.remove("drag-over"); if (event.dataTransfer.files[0]) chooseFile(event.dataTransfer.files[0]); });
ui.removeFile.addEventListener("click", resetFile);
ui.source.addEventListener("input", updateForm);
$("clearTextBtn").addEventListener("click", () => { ui.source.value = ""; updateForm(); });
$("uploadTab").addEventListener("click", () => { $("uploadPanel").classList.remove("hidden"); $("pastePanel").classList.add("hidden"); $("uploadTab").classList.add("active"); $("pasteTab").classList.remove("active"); });
$("pasteTab").addEventListener("click", () => { $("pastePanel").classList.remove("hidden"); $("uploadPanel").classList.add("hidden"); $("pasteTab").classList.add("active"); $("uploadTab").classList.remove("active"); });
document.querySelectorAll(".mode-option").forEach((button) => button.addEventListener("click", () => { mode = button.dataset.mode; document.querySelectorAll(".mode-option").forEach((option) => option.classList.toggle("selected", option === button)); }));
document.querySelectorAll(".content-tab").forEach((button) => button.addEventListener("click", () => { document.querySelectorAll(".content-tab").forEach((tab) => tab.classList.toggle("active", tab === button)); document.querySelectorAll(".content-view").forEach((view) => view.classList.toggle("hidden", view.id !== `${button.dataset.view}View`)); }));
ui.quizList.addEventListener("click", (event) => { const button = event.target.closest(".check-answer"); if (button) checkQuizAnswer(button.closest(".quiz-item")); });
ui.tutorForm.addEventListener("submit", askTutor);
ui.deckMapList.addEventListener("click", (event) => { const card = event.target.closest(".deck-slide"); if (!card) return; document.querySelectorAll(".deck-slide").forEach((item) => item.classList.toggle("selected", item === card)); const slide = lesson.slides?.[Number(card.dataset.slideIndex)]; if (slide) { speak(slide.text); showToast(`Playing slide ${slide.number || Number(card.dataset.slideIndex) + 1}`); } });
ui.narration.addEventListener("click", (event) => { const paragraph = event.target.closest(".narration-paragraph"); if (paragraph) speak(paragraph.innerText.replace(/^\d+\s*/, ""), Number(paragraph.dataset.paragraphIndex)); });
ui.narration.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { const paragraph = event.target.closest(".narration-paragraph"); if (paragraph) { event.preventDefault(); speak(paragraph.innerText.replace(/^\d+\s*/, ""), Number(paragraph.dataset.paragraphIndex)); } } });
ui.historyList.addEventListener("click", (event) => { const item = event.target.closest(".history-item"); if (item) restoreHistory(Number(item.dataset.historyIndex)); });
ui.clearHistory.addEventListener("click", () => { localStorage.removeItem("lectureLensHistory"); renderHistory(); showToast("History cleared"); });
ui.generate.addEventListener("click", () => createLesson());
ui.demo.addEventListener("click", () => createLesson(true));
ui.heroDemo.addEventListener("click", () => { $("studio").scrollIntoView({ behavior: "smooth" }); setTimeout(() => createLesson(true), 450); });
$("dismissErrorBtn").addEventListener("click", hideError);
ui.play.addEventListener("click", () => { if (window.speechSynthesis.paused) window.speechSynthesis.resume(); else if (window.speechSynthesis.speaking) window.speechSynthesis.pause(); else speak(); });
ui.restart.addEventListener("click", () => speak());
ui.stop.addEventListener("click", stopSpeech);
ui.replayKey.addEventListener("click", () => speak(lesson?.key_points?.[0]));
ui.speed.addEventListener("input", () => { ui.speedValue.textContent = `${Number(ui.speed.value).toFixed(1)}x`; });
ui.copy.addEventListener("click", async () => { await navigator.clipboard.writeText(lesson.narration); showToast("Narration copied"); });
ui.download.addEventListener("click", () => { const content = `${lesson.title}\n\n${lesson.narration}\n\nKey takeaways\n${lesson.key_points.map((point) => `- ${point}`).join("\n")}`; const link = document.createElement("a"); link.href = URL.createObjectURL(new Blob([content], { type: "text/plain" })); link.download = `${lesson.title || "lecture"}-notes.txt`; link.click(); });
ui.newLesson.addEventListener("click", () => { stopSpeech(); ui.lesson.classList.add("hidden"); $("studio").scrollIntoView({ behavior: "smooth" }); });

function showToast(message) { ui.toast.textContent = message; ui.toast.classList.remove("hidden"); setTimeout(() => ui.toast.classList.add("hidden"), 2200); }
function loadVoices() { const voices = window.speechSynthesis.getVoices().filter((voiceOption) => voiceOption.lang.startsWith("en")); ui.voice.innerHTML = voices.map((voiceOption) => `<option>${escapeHtml(voiceOption.name)}</option>`).join("") || "<option>Default device voice</option>"; }

checkHealth();
updateForm();
renderHistory();
if ("speechSynthesis" in window) { loadVoices(); window.speechSynthesis.onvoiceschanged = loadVoices; }