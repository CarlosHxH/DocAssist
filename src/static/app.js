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
const themeBtn = document.querySelector("#theme-toggle");

const HISTORY_KEY = "docassist_history_v2";
const THEME_KEY = "docassist_theme";

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

// ---------- tema ----------

function applyTheme(theme) {
  const dark = theme === "dark";
  document.documentElement.dataset.theme = theme;
  const label = dark ? "Ativar modo claro" : "Ativar modo escuro";
  themeBtn.setAttribute("aria-label", label);
  themeBtn.title = label;
  themeBtn.setAttribute("aria-pressed", String(dark));
}

themeBtn.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  applyTheme(next);
  try {
    localStorage.setItem(THEME_KEY, next);
  } catch (err) {
    /* armazenamento indisponível — o tema vale só para esta sessão */
  }
});

applyTheme(document.documentElement.dataset.theme || "light");

// ---------- coleta de erros do navegador ----------

const MAX_CLIENT_REPORTS = 20;
const reportedErrors = new Set();

// Envia erros de JavaScript para o servidor (logs/docassist.log), que de outra forma só
// apareceriam no console do navegador do usuário. Limitado e sem duplicatas por página.
function reportClientError({ message, source = "", stack = "", level = "error" }) {
  try {
    const key = `${message}|${source}`;
    if (reportedErrors.has(key) || reportedErrors.size >= MAX_CLIENT_REPORTS) return;
    reportedErrors.add(key);
    const body = JSON.stringify({
      level,
      message: String(message).slice(0, 2000),
      source: String(source).slice(0, 500),
      stack: String(stack || "").slice(0, 2000),
      url: location.pathname,
      user_agent: navigator.userAgent,
    });
    fetch("/api/client-log", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      keepalive: true,
    }).catch(() => {});
  } catch (err) {
    /* coleta de log nunca pode quebrar a interface */
  }
}

window.addEventListener("error", (event) => {
  reportClientError({
    message: event.message || "Erro de script",
    source: event.filename ? `${event.filename}:${event.lineno}:${event.colno}` : "",
    stack: event.error && event.error.stack,
  });
});

window.addEventListener("unhandledrejection", (event) => {
  const reason = event.reason || {};
  reportClientError({
    message: `Promise rejeitada: ${reason.message || reason}`,
    source: "unhandledrejection",
    stack: reason.stack,
  });
});

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

// ---------- markdown ----------
// Renderizador mínimo, sem dependências nem CDN: cobre o que o modelo e os documentos de
// rag/ usam (títulos, listas aninhadas, tabelas, citações, blocos de código e formatação
// inline). Todo texto é escapado antes de virar HTML, então a resposta não injeta tags.

const LIST_RE = /^(\s*)([-*+]|\d+[.)])\s+(.*)$/;
const FENCE_RE = /^\s*(```|~~~)\s*([\w+#.-]*)\s*$/;
const HR_RE = /^\s*([-*_])(\s*\1){2,}\s*$/;
const HEADING_RE = /^(#{1,6})\s+(.+?)\s*#*\s*$/;
const TABLE_SEP_RE = /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/;

function renderInline(text) {
  // Código inline é separado antes, para que nada dentro dele vire negrito/link.
  const codes = [];
  let out = text.replace(/`([^`]+)`/g, (_, code) => {
    codes.push(code);
    return `\u0000${codes.length - 1}\u0000`;
  });
  out = escapeHtml(out)
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
    .replace(/\*\*(?!\s)([^\n]+?(?:\n[^\n]+?)?)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^\w])__(?!\s)(.+?)__(?!\w)/g, "$1<strong>$2</strong>")
    .replace(/(^|[^*\w])\*(?![\s*])(.+?)\*(?!\w)/g, "$1<em>$2</em>")
    .replace(/(^|[^\w])_(?![\s_])(.+?)_(?!\w)/g, "$1<em>$2</em>")
    .replace(/~~(.+?)~~/g, "<del>$1</del>");
  return out.replace(/\u0000(\d+)\u0000/g, (_, i) => `<code>${escapeHtml(codes[i])}</code>`);
}

function codeBlockHtml(code, lang) {
  const label = lang ? escapeHtml(lang) : "exemplo";
  return (
    `<div class="code-block"><div class="code-head"><span>${label}</span>` +
    `<button type="button" class="code-copy">Copiar</button></div>` +
    `<pre><code>${escapeHtml(code)}</code></pre></div>`
  );
}

function leadingSpaces(line) {
  return line.match(/^\s*/)[0].length;
}

function dedent(lines) {
  const indent = Math.min(...lines.filter((l) => l.trim()).map(leadingSpaces));
  return lines.map((l) => l.slice(Math.min(indent, leadingSpaces(l))));
}

function splitRow(line) {
  return line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((cell) => cell.trim());
}

function renderTable(lines, start) {
  const header = splitRow(lines[start]);
  const aligns = splitRow(lines[start + 1]).map((cell) =>
    cell.startsWith(":") && cell.endsWith(":") ? "center" : cell.endsWith(":") ? "right" : ""
  );
  const cell = (tag, text, col) =>
    `<${tag}${aligns[col] ? ` style="text-align:${aligns[col]}"` : ""}>${renderInline(text || "")}</${tag}>`;
  let i = start + 2;
  const rows = [];
  while (i < lines.length && lines[i].includes("|") && lines[i].trim()) {
    rows.push(`<tr>${header.map((_, col) => cell("td", splitRow(lines[i])[col], col)).join("")}</tr>`);
    i++;
  }
  const head = `<tr>${header.map((text, col) => cell("th", text, col)).join("")}</tr>`;
  return [`<div class="table-wrap"><table><thead>${head}</thead><tbody>${rows.join("")}</tbody></table></div>`, i];
}

function renderList(lines, start) {
  const first = lines[start].match(LIST_RE);
  const indent = first[1].length;
  const ordered = /\d/.test(first[2]);
  const items = [];
  let i = start;
  while (i < lines.length) {
    const line = lines[i];
    const m = line.match(LIST_RE);
    if (m && m[1].length === indent && /\d/.test(m[2]) === ordered) {
      items.push({ text: m[3], children: [] });
    } else if (line.trim() && leadingSpaces(line) > indent) {
      items[items.length - 1].children.push(line); // sublista ou continuação do item
    } else if (!line.trim()) {
      // Linha em branco só continua a lista se o próximo item ainda pertencer a ela.
      const next = lines[i + 1] || "";
      const nm = next.match(LIST_RE);
      if (!(nm && nm[1].length >= indent) && !(next.trim() && leadingSpaces(next) > indent)) break;
    } else {
      break;
    }
    i++;
  }
  const tag = ordered ? "ol" : "ul";
  const startAttr = ordered && parseInt(first[2], 10) !== 1 ? ` start="${parseInt(first[2], 10)}"` : "";
  const body = items
    .map((item) => `<li>${renderInline(item.text)}${item.children.length ? renderBlocks(dedent(item.children)) : ""}</li>`)
    .join("");
  return [`<${tag}${startAttr}>${body}</${tag}>`, i];
}

function isBlockStart(lines, i) {
  const line = lines[i];
  return (
    FENCE_RE.test(line) || HEADING_RE.test(line) || HR_RE.test(line) || /^\s*>/.test(line) ||
    LIST_RE.test(line) || (line.includes("|") && TABLE_SEP_RE.test(lines[i + 1] || ""))
  );
}

function renderBlocks(lines) {
  const html = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) {
      i++;
      continue;
    }

    const fence = line.match(FENCE_RE);
    if (fence) {
      const body = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith(fence[1])) body.push(lines[i++]);
      i++; // pula o fechamento (ou o fim do texto, se o modelo não fechou o bloco)
      html.push(codeBlockHtml(dedent(body).join("\n"), fence[2]));
      continue;
    }

    const heading = line.match(HEADING_RE);
    if (heading) {
      // Dentro de uma mensagem, "#" vira h3: os títulos não competem com os da página.
      const level = Math.min(heading[1].length + 2, 6);
      html.push(`<h${level}>${renderInline(heading[2])}</h${level}>`);
      i++;
      continue;
    }

    if (HR_RE.test(line)) {
      html.push("<hr>");
      i++;
      continue;
    }

    if (/^\s*>/.test(line)) {
      const quoted = [];
      while (i < lines.length && /^\s*>/.test(lines[i])) quoted.push(lines[i++].replace(/^\s*>\s?/, ""));
      html.push(`<blockquote>${renderBlocks(quoted)}</blockquote>`);
      continue;
    }

    if (line.includes("|") && TABLE_SEP_RE.test(lines[i + 1] || "")) {
      const [table, next] = renderTable(lines, i);
      html.push(table);
      i = next;
      continue;
    }

    if (LIST_RE.test(line)) {
      const [list, next] = renderList(lines, i);
      html.push(list);
      i = next;
      continue;
    }

    // Parágrafo: quebras de linha simples são mantidas, como o modelo as escreveu.
    // O parágrafo é renderizado inteiro, para que um **negrito** possa atravessar a quebra.
    const para = [];
    while (i < lines.length && lines[i].trim() && (para.length === 0 || !isBlockStart(lines, i))) {
      para.push(lines[i].trim());
      i++;
    }
    html.push(`<p>${renderInline(para.join("\n")).replace(/\n/g, "<br>")}</p>`);
  }
  return html.join("");
}

function renderMarkdown(text) {
  return renderBlocks(text.replace(/\r\n?/g, "\n").split("\n"));
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
    content.className = "md";
    content.innerHTML = renderMarkdown(cleaned);
  }
  article.append(content);

  if (entry.role === "assistant" && entry.status === "ok") {
    (entry.sourcesDetail || []).forEach((source) => {
      const details = document.createElement("details");
      const summary = document.createElement("summary");
      const body = document.createElement("div");
      summary.textContent = `Fonte recuperada · ${source.title} — ${source.heading}`;
      body.className = "md source";
      body.innerHTML = renderMarkdown(source.text);
      details.append(summary, body);
      article.append(details);
    });

    const copyBtn = document.createElement("button");
    copyBtn.type = "button";
    copyBtn.className = "copy-btn";
    copyBtn.textContent = "Copiar resposta";
    copyBtn.addEventListener("click", () => copyToClipboard(cleaned, copyBtn, "Resposta copiada."));
    article.append(copyBtn);
  }

  // Botão "Copiar" de cada bloco de código (resposta e fontes).
  article.querySelectorAll(".code-copy").forEach((btn) => {
    btn.addEventListener("click", () =>
      copyToClipboard(btn.closest(".code-block").querySelector("code").textContent, btn, "Exemplo copiado.")
    );
  });

  const meta = [];
  if (typeof entry.latency === "number") meta.push(`${entry.latency.toFixed(1)}s`);
  // Em erros, o código permite achar a requisição em logs/docassist.log e interactions.jsonl.
  if (entry.status === "erro" && entry.requestId) meta.push(`código do erro: ${entry.requestId}`);
  if (meta.length) {
    const latency = document.createElement("p");
    latency.className = "latency";
    latency.textContent = meta.join(" · ");
    article.append(latency);
  }

  return article;
}

function copyToClipboard(text, btnEl, successMessage) {
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
      showToast(successMessage, "success", 2000);
    })
    .catch(() => showToast("Não foi possível copiar.", "error"));
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

    if (!data) {
      reportClientError({
        message: `Resposta não-JSON de /api/ask (HTTP ${response.status})`,
        source: "submit",
        level: "warning",
      });
      throw new Error("Resposta inválida do servidor.");
    }

    const assistantEntry = {
      role: "assistant",
      text: data.answer || "(sem resposta)",
      status: data.status || "erro",
      sourcesDetail: data.sources_detail || [],
      latency: data.latency_seconds,
      requestId: data.request_id || response.headers.get("X-Request-ID"),
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
