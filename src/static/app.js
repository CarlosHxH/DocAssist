const chat = document.querySelector("#chat");
const input = document.querySelector("#question");
const sendBtn = document.querySelector("#send");
const clearBtn = document.querySelector("#clear");
const introEl = document.querySelector("#intro");
const statusEl = document.querySelector("#status");
const docCountEl = document.querySelector("#doc-count");
const docNamesEl = document.querySelector("#doc-names");
const confirmDialog = document.querySelector("#confirm-dialog");
const toastsEl = document.querySelector("#toasts");

const HISTORY_KEY = "docassist_history_v2";

let history = loadHistory();
let busy = false;
let serverOnline = null;

// ---------- armazenamento local ----------

function loadHistory() {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (err) {
    return [];
  }
}

function saveHistory() {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(-60)));
  } catch (err) {
    /* armazenamento indisponível (ex. aba privada) — segue sem persistir */
  }
}

// ---------- alertas ----------

function showToast(message, type = "info", duration = 3200) {
  const toast = document.createElement("div");
  toast.className = "toast " + type;
  toast.setAttribute("role", type === "error" ? "alert" : "status");

  const text = document.createElement("span");
  text.textContent = message;
  const close = document.createElement("button");
  close.type = "button";
  close.className = "toast-close";
  close.setAttribute("aria-label", "Fechar aviso");
  close.textContent = "×";

  toast.append(text, close);
  toastsEl.append(toast);

  let timer;
  const dismiss = () => {
    clearTimeout(timer);
    toast.classList.add("leaving");
    toast.addEventListener("animationend", () => toast.remove(), { once: true });
  };
  close.addEventListener("click", dismiss);
  if (duration > 0) timer = setTimeout(dismiss, duration);
}

function showConfirm({ title = "Confirmar", message = "", confirmText = "Confirmar", cancelText = "Cancelar" } = {}) {
  const cancelBtn = confirmDialog.querySelector("button[value=cancel]");
  confirmDialog.querySelector("#confirm-title").textContent = title;
  confirmDialog.querySelector("#confirm-message").textContent = message;
  confirmDialog.querySelector("#confirm-ok").textContent = confirmText;
  cancelBtn.textContent = cancelText;
  confirmDialog.returnValue = "cancel";

  return new Promise((resolve) => {
    confirmDialog.addEventListener("close", () => resolve(confirmDialog.returnValue === "ok"), { once: true });
    confirmDialog.showModal();
    cancelBtn.focus();
  });
}

// fecha ao clicar fora da caixa
confirmDialog.addEventListener("click", (event) => {
  if (event.target === confirmDialog) confirmDialog.close("cancel");
});

// ---------- texto ----------

function escapeHtml(str) {
  return str.replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
}

function cleanAnswerText(text) {
  return text.replace(/\[\s*fonte\s*:[^\]]*\]/gi, "").trim();
}

function formatInlineCode(escapedText) {
  return escapedText.replace(/`([^`]+)`/g, "<code>$1</code>");
}

// ---------- renderização ----------

function renderMessage(entry) {
  const article = document.createElement("article");
  article.className = "message " + entry.role;

  const label = document.createElement("div");
  label.className = "label";
  label.textContent = entry.role === "user" ? "VOCÊ" : "ASSISTENTE · DOCASSIST";
  article.append(label);

  const content = document.createElement("div");
  const cleaned = entry.role === "assistant" ? cleanAnswerText(entry.text) : entry.text;

  if (entry.role === "user") {
    content.className = "text";
    content.textContent = cleaned;
  } else if (entry.status === "sem_contexto") {
    content.className = "text warning";
    content.textContent = cleaned;
  } else if (entry.status === "erro") {
    content.className = "text error";
    content.textContent = cleaned;
  } else {
    content.className = "text";
    content.innerHTML = formatInlineCode(escapeHtml(cleaned));
  }
  article.append(content);

  if (entry.role === "assistant" && entry.status === "ok") {
    (entry.sourcesDetail || []).forEach((source) => {
      const details = document.createElement("details");
      const summary = document.createElement("summary");
      const pre = document.createElement("pre");
      summary.textContent = `Fonte recuperada · ${source.title} — ${source.heading}`;
      pre.textContent = source.text;
      details.append(summary, pre);
      article.append(details);
    });

    const copyBtn = document.createElement("button");
    copyBtn.type = "button";
    copyBtn.className = "copy-btn";
    copyBtn.textContent = "Copiar resposta";
    copyBtn.addEventListener("click", () => copyToClipboard(cleaned, copyBtn));
    article.append(copyBtn);
  }

  if (typeof entry.latency === "number") {
    const latency = document.createElement("p");
    latency.className = "latency";
    latency.textContent = `${entry.latency.toFixed(1)}s`;
    article.append(latency);
  }

  return article;
}

function copyToClipboard(text, btnEl) {
  if (!navigator.clipboard || !navigator.clipboard.writeText) {
    showToast("Área de transferência indisponível neste navegador.", "error");
    return;
  }
  navigator.clipboard
    .writeText(text)
    .then(() => {
      const original = btnEl.textContent;
      btnEl.textContent = "Copiado ✓";
      setTimeout(() => { btnEl.textContent = original; }, 1500);
      showToast("Resposta copiada.", "success", 2000);
    })
    .catch(() => showToast("Não foi possível copiar a resposta.", "error"));
}

function renderAll() {
  chat.replaceChildren();
  history.forEach((entry) => chat.append(renderMessage(entry)));
  introEl.hidden = history.length > 0;
  chat.scrollTop = chat.scrollHeight;
}

function addTyping() {
  const article = document.createElement("article");
  article.className = "message assistant typing";
  const label = document.createElement("div");
  label.className = "label";
  label.textContent = "ASSISTENTE · DOCASSIST";
  const content = document.createElement("div");
  content.className = "text";
  content.style.color = "#8aa0a9";
  content.textContent = "Consultando trechos e gerando resposta na CPU…";
  article.append(label, content);
  chat.append(article);
  article.scrollIntoView({ behavior: "smooth", block: "end" });
  return article;
}

// ---------- status do backend ----------

async function refreshStatus() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) throw new Error("bad status");
    const s = await response.json();
    statusEl.classList.toggle("offline", !s.ready);
    statusEl.textContent =
      (s.ready ? "● Modelo disponível" : "○ Modelo indisponível") +
      `\n${s.generation_model} · CPU\n${s.docs} documentos · ${s.chunks} trechos`;
    docCountEl.textContent = `${s.docs} documentos`;
    // docNamesEl.textContent = (s.doc_titles || s.doc_names || []).join(" · ");
    if (serverOnline === false) showToast("Conexão com o servidor restabelecida.", "success");
    serverOnline = true;
  } catch (err) {
    statusEl.classList.add("offline");
    statusEl.textContent = "Servidor indisponível.";
    if (serverOnline !== false) showToast("Servidor do DocAssist indisponível.", "error", 5000);
    serverOnline = false;
  }
}

// ---------- fluxo de pergunta ----------

async function submit(question) {
  question = question.trim();
  if (busy || !question) return;
  busy = true;
  sendBtn.disabled = true;
  clearBtn.disabled = true;
  input.disabled = true;
  introEl.hidden = true;

  const userEntry = { role: "user", text: question };
  history.push(userEntry);
  saveHistory();
  chat.append(renderMessage(userEntry));
  input.value = "";
  autoScrollToEnd();

  const typingEl = addTyping();

  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await response.json().catch(() => null);
    typingEl.remove();

    if (!data) throw new Error("Resposta inválida do servidor.");

    const assistantEntry = {
      role: "assistant",
      text: data.answer || "(sem resposta)",
      status: data.status || "erro",
      sourcesDetail: data.sources_detail || [],
      latency: data.latency_seconds,
    };
    history.push(assistantEntry);
    saveHistory();
    chat.append(renderMessage(assistantEntry));
    if (assistantEntry.status === "erro") input.value = question;
  } catch (err) {
    typingEl.remove();
    const failEntry = {
      role: "assistant",
      text: "Não foi possível falar com o servidor do DocAssist. Verifique se `python web_server.py` está rodando.",
      status: "erro",
    };
    history.push(failEntry);
    saveHistory();
    chat.append(renderMessage(failEntry));
    input.value = question;
  } finally {
    busy = false;
    sendBtn.disabled = false;
    clearBtn.disabled = false;
    input.disabled = false;
    autoScrollToEnd();
    input.focus();
  }
}

function autoScrollToEnd() {
  chat.scrollTop = chat.scrollHeight;
}

// ---------- eventos ----------

document.querySelector("#form").addEventListener("submit", (event) => {
  event.preventDefault();
  submit(input.value);
});

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    submit(input.value);
  }
});

document.querySelectorAll(".suggestions button").forEach((button) => {
  button.addEventListener("click", () => submit(button.textContent));
});

clearBtn.addEventListener("click", async () => {
  if (history.length === 0) {
    showToast("A conversa já está vazia.");
    return;
  }
  const confirmed = await showConfirm({
    title: "Nova conversa",
    message: "Todo o histórico desta conversa será apagado. Deseja continuar?",
    confirmText: "Limpar conversa",
  });
  if (!confirmed) return;
  history = [];
  saveHistory();
  renderAll();
  showToast("Conversa limpa.", "success", 2000);
  input.focus();
});

renderAll();
refreshStatus();
setInterval(refreshStatus, 30000);
input.focus();
