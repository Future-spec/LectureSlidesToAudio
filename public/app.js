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
  toast: $("toast"),
};

let file = null;
let lesson = null;
let mode = "explainer";
let utterance = null;
let timer = null;

function setStatus(online, label) {
  ui.status.innerHTML = `<span class="status-dot ${online ? "online" : "offline"}"></span><span>${label}</span>`;
}

async function requestJson(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok || data.error) throw new Error(data.error || "The request could not be completed.");
  return data;
}

async function checkHealth() {
  try {
    const response = await fetch("/api/health");
    setStatus(response.ok, response.ok ? "Studio ready" : "Studio limited");
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
      extracted = { extracted_text: ui.source.value.trim(), meta: { source: "pasted text", pages: 1 } };
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
    lesson = { ...result, extracted_text: extracted.extracted_text, meta: result.meta || extracted.meta };
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
  ui.lessonTitle.textContent = `${title} is ready`;
  ui.narrationTitle.textContent = title;
  ui.lessonMeta.textContent = `${lesson.meta?.engine || "Smart offline guide"} · ${lesson.meta?.pages || 1} page · ${lesson.meta?.characters || lesson.extracted_text.length} characters`;
  ui.engine.textContent = lesson.meta?.engine || "AI guided";
  ui.narration.innerHTML = lesson.narration.split(/\n\s*\n/).map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("");
  ui.takeaways.innerHTML = (lesson.key_points || []).map((point) => `<li>${escapeHtml(point)}</li>`).join("");
  ui.takeawayCount.textContent = lesson.key_points?.length || 0;
  ui.sourceContent.textContent = lesson.extracted_text;
  ui.memory.textContent = lesson.key_points?.[0] || "Replay the lesson once, then explain the main idea in your own words.";
  ui.total.textContent = formatTime(estimateSeconds(lesson.narration));
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
  utterance.onend = stopSpeech;
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
if ("speechSynthesis" in window) { loadVoices(); window.speechSynthesis.onvoiceschanged = loadVoices; }