/* ── Lecture Slides to Audio — Client-Side Logic ─────────── */

// DOM references
const dropZone     = document.getElementById("dropZone");
const dropLabel    = document.getElementById("dropLabel");
const fileInput    = document.getElementById("fileInput");
const processBtn   = document.getElementById("processBtn");
const demoBtn      = document.getElementById("demoBtn");
const progressEl   = document.getElementById("progress");
const resultsEl    = document.getElementById("results");
const errorEl      = document.getElementById("error");
const extractedEl  = document.getElementById("extractedText");
const narrationEl  = document.getElementById("narrationText");
const playBtn      = document.getElementById("playBtn");
const pauseBtn     = document.getElementById("pauseBtn");
const stopBtn      = document.getElementById("stopBtn");
const speedRange   = document.getElementById("speedRange");
const speedValue   = document.getElementById("speedValue");

let selectedFile = null;
let utterance    = null;   // current SpeechSynthesisUtterance

// ── File Selection ──────────────────────────────────────────

dropZone.addEventListener("click", () => fileInput.click());

dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("drag-over");
});

dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("drag-over");
});

dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});

fileInput.addEventListener("change", () => {
    if (fileInput.files.length) handleFile(fileInput.files[0]);
});

function handleFile(file) {
    const allowed = [
        "image/jpeg", "image/png", "image/webp", "application/pdf",
    ];
    if (!allowed.includes(file.type)) {
        showError("Please upload a JPG, PNG, or PDF file.");
        return;
    }
    if (file.size > 4.5 * 1024 * 1024) {
        showError("File is too large. Maximum size is 4.5 MB.");
        return;
    }
    selectedFile = file;
    dropLabel.textContent = `✅ ${file.name}`;
    dropZone.classList.add("has-file");
    processBtn.disabled = false;
    hideError();
}

// ── Demo Mode ───────────────────────────────────────────────

demoBtn.addEventListener("click", async () => {
    resetUI();
    showProgress();
    setStep(1, "active");
    setStep(2, "active");

    try {
        const res  = await fetch("/api/demo");
        const data = await res.json();

        setStep(3, "active");
        // Small delay so the user sees the steps animate
        await delay(400);
        setStep(4, "active");

        showResults(data.extracted_text, data.narration);
    } catch (err) {
        showError("Demo failed: " + err.message);
    }
});

// ── Process Real File ───────────────────────────────────────

processBtn.addEventListener("click", async () => {
    if (!selectedFile) return;
    resetUI();
    showProgress();

    try {
        // Step 1-2: Extract text
        setStep(1, "loading");
        const form = new FormData();
        form.append("file", selectedFile);

        setStep(2, "loading");
        const extRes  = await fetch("/api/extract", { method: "POST", body: form });
        const extData = await extRes.json();

        if (extData.error) throw new Error(extData.error);
        setStep(1, "active");
        setStep(2, "active");

        // Step 3: Generate narration
        setStep(3, "loading");
        const narRes  = await fetch("/api/narrate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: extData.extracted_text }),
        });
        const narData = await narRes.json();

        if (narData.error) throw new Error(narData.error);
        setStep(3, "active");

        // Step 4: Done
        setStep(4, "active");
        showResults(extData.extracted_text, narData.narration);

    } catch (err) {
        showError(err.message);
    }
});

// ── Text-to-Speech (Browser Web Speech API) ─────────────────

playBtn.addEventListener("click", () => {
    const text = narrationEl.textContent;
    if (!text) return;

    // Cancel any ongoing speech
    speechSynthesis.cancel();

    utterance      = new SpeechSynthesisUtterance(text);
    utterance.rate = parseFloat(speedRange.value);
    utterance.lang = "en-US";

    utterance.onstart = () => {
        playBtn.disabled  = true;
        pauseBtn.disabled = false;
        stopBtn.disabled  = false;
    };

    utterance.onend = () => {
        playBtn.disabled  = false;
        pauseBtn.disabled = true;
        stopBtn.disabled  = true;
        pauseBtn.textContent = "⏸ Pause";
    };

    speechSynthesis.speak(utterance);
});

pauseBtn.addEventListener("click", () => {
    if (speechSynthesis.paused) {
        speechSynthesis.resume();
        pauseBtn.textContent = "⏸ Pause";
    } else {
        speechSynthesis.pause();
        pauseBtn.textContent = "▶ Resume";
    }
});

stopBtn.addEventListener("click", () => {
    speechSynthesis.cancel();
    playBtn.disabled  = false;
    pauseBtn.disabled = true;
    stopBtn.disabled  = true;
    pauseBtn.textContent = "⏸ Pause";
});

speedRange.addEventListener("input", () => {
    speedValue.textContent = speedRange.value + "×";
});

// ── UI Helpers ──────────────────────────────────────────────

function resetUI() {
    progressEl.classList.add("hidden");
    resultsEl.classList.add("hidden");
    errorEl.classList.add("hidden");
    speechSynthesis.cancel();
    playBtn.disabled  = false;
    pauseBtn.disabled = true;
    stopBtn.disabled  = true;

    // Reset all steps
    for (let i = 1; i <= 4; i++) {
        const el = document.getElementById("step" + i);
        el.classList.remove("active", "loading");
        el.querySelector(".dot").textContent = "○";
    }
}

function showProgress() {
    progressEl.classList.remove("hidden");
}

function setStep(n, state) {
    const el  = document.getElementById("step" + n);
    const dot = el.querySelector(".dot");

    el.classList.remove("active", "loading");
    el.classList.add(state);

    if (state === "active")  dot.textContent = "✓";
    if (state === "loading") dot.textContent = "◌";
}

function showResults(extracted, narration) {
    extractedEl.textContent = extracted;
    narrationEl.textContent = narration;
    resultsEl.classList.remove("hidden");
}

function showError(msg) {
    errorEl.textContent = "⚠ " + msg;
    errorEl.classList.remove("hidden");
}

function hideError() {
    errorEl.classList.add("hidden");
}

function delay(ms) {
    return new Promise((r) => setTimeout(r, ms));
}

