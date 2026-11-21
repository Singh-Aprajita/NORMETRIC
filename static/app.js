let transactions = [];
let dashboardData = null;

const money = v =>
    "₹" + Number(v || 0).toLocaleString("en-IN", {
        maximumFractionDigits: 0
    });

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

async function api(url, opts = {}) {
    const r = await fetch(url, opts);
    const d = await r.json();

    if (!r.ok) {
        throw new Error(d.detail || "Request failed");
    }

    return d;
}


// --------------------------------
// PAGE NAVIGATION
// --------------------------------

function showPage(name) {
    document.querySelectorAll(".page").forEach(p =>
        p.classList.add("hidden")
    );

    const page = document.getElementById("page-" + name);

    if (page) {
        page.classList.remove("hidden");
    }

    document.querySelectorAll(".nav-link").forEach(b =>
        b.classList.toggle("active", b.dataset.page === name)
    );

    history.replaceState(null, "", "#" + name);

    if (name === "transactions") {
        renderTransactions();
    }

    if (name === "analytics" || name === "dashboard") {
        drawCharts();
    }

    window.scrollTo({ top: 0, behavior: "smooth" });
}

function badge(level) {
    return `<span class="risk ${level}">${level}</span>`;
}

function recentRow(t) {
    return `
        <tr>
            <td><b>${escapeHtml(t.transaction_id)}</b></td>
            <td>${escapeHtml(t.customer_id)}</td>
            <td>${money(t.amount)}</td>
            <td>${escapeHtml(t.city)}</td>
            <td>${t.risk_score}/100</td>
            <td>${badge(t.risk_level)}</td>
            <td>${escapeHtml(t.decision)}</td>
        </tr>
    `;
}


// --------------------------------
// TRANSACTION EXPLORER
// --------------------------------

function renderTransactions() {
    const q = (
        document.getElementById("search")?.value || ""
    ).toLowerCase();

    const level =
        document.getElementById("riskFilter")?.value || "";

    const rows = transactions.filter(t =>
        (!level || t.risk_level === level) &&
        [
            t.transaction_id,
            t.customer_id,
            t.city
        ].join(" ").toLowerCase().includes(q)
    );

    const el = document.getElementById("allRows");

    if (!el) return;

    el.innerHTML = rows.length
        ? rows.map(t => `
            <tr>
                <td>${escapeHtml(t.transaction_id)}</td>
                <td>${escapeHtml(t.customer_id)}</td>
                <td>${money(t.amount)}</td>
                <td>${escapeHtml(t.city)}</td>
                <td>${t.risk_score}/100</td>
                <td>${badge(t.risk_level)}</td>
                <td>
                    <button
                        class="ai-explain-btn"
                        type="button"
                        data-transaction-id="${escapeHtml(t.transaction_id)}">
                        Explain with AI
                    </button>
                </td>
            </tr>
        `).join("")
        : `
            <tr>
                <td colspan="7" class="empty">
                    No matching transactions.
                </td>
            </tr>
        `;
}


// --------------------------------
// GEMINI AI TRANSACTION EXPLANATION
// --------------------------------

async function explainWithAI(transactionId, button) {
    const dialog =
        document.getElementById("aiExplanationDialog");

    const title =
        document.getElementById("aiExplanationTitle");

    const content =
        document.getElementById("aiExplanationContent");

    const status =
        document.getElementById("aiExplanationStatus");

    if (!dialog || !title || !content || !status) {
        return;
    }

    title.textContent = `AI explanation · ${transactionId}`;

    content.textContent = "";

    status.textContent =
        "Gemini is analysing the saved transaction assessment…";

    if (typeof dialog.showModal === "function") {
        dialog.showModal();
    } else {
        dialog.setAttribute("open", "");
    }

    if (button) {
        button.disabled = true;
    }

    try {
        const result = await api(
            `/api/ai/explain/${encodeURIComponent(transactionId)}`,
            { method: "POST" }
        );

        content.textContent =
            result.explanation ||
            "The AI service returned no explanation.";

        status.textContent =
            "Generated from the transaction assessment stored in NORMETRIC.";

    } catch (error) {
        content.textContent =
            "The explanation could not be generated.";

        status.textContent =
            error.message ||
            "AI service unavailable. Please try again.";

    } finally {
        if (button) {
            button.disabled = false;
        }
    }
}


// --------------------------------
// HANDLE AI BUTTON CLICKS
// --------------------------------

document.getElementById("allRows")?.addEventListener(
    "click",
    event => {
        const button = event.target.closest(".ai-explain-btn");

        if (!button || button.disabled) {
            return;
        }

        explainWithAI(button.dataset.transactionId, button);
    }
);


// --------------------------------
// BAR CHART
// --------------------------------

function drawBarChart(canvasId, labels, values, colors) {
    const c = document.getElementById(canvasId);

    if (!c) return;

    const ctx = c.getContext("2d");
    const w = c.clientWidth || 500;
    const h = c.clientHeight || 240;
    const dpr = window.devicePixelRatio || 1;

    c.width = w * dpr;
    c.height = h * dpr;

    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);

    const pad = {
        l: 34,
        r: 15,
        t: 18,
        b: 36
    };

    const cw = w - pad.l - pad.r;
    const ch = h - pad.t - pad.b;

    const max = Math.max(1, ...values);

    ctx.strokeStyle = "#2a3954";
    ctx.lineWidth = 1;

    for (let i = 0; i < 4; i++) {
        let y = pad.t + ch * i / 3;

        ctx.beginPath();
        ctx.moveTo(pad.l, y);
        ctx.lineTo(w - pad.r, y);
        ctx.stroke();
    }

    const gap = cw / labels.length;
    const bw = Math.min(62, gap * 0.48);

    values.forEach((v, i) => {
        let bh = (v / max) * (ch - 8);

        let x = pad.l + gap * i + (gap - bw) / 2;
        let y = pad.t + ch - bh;

        ctx.fillStyle = colors[i];

        ctx.beginPath();
        ctx.roundRect(x, y, bw, bh, 6);
        ctx.fill();

        ctx.fillStyle = "#aab8d0";
        ctx.font = "10px DM Sans";
        ctx.textAlign = "center";

        ctx.fillText(String(v), x + bw / 2, y - 7);
        ctx.fillText(labels[i], x + bw / 2, h - 11);
    });
}


// --------------------------------
// RISK SCORE CHART
// --------------------------------

function drawScoreChart() {
    const c = document.getElementById("scoreChart");

    if (!c) return;

    const ctx = c.getContext("2d");

    const w = c.clientWidth || 500;
    const h = c.clientHeight || 260;
    const dpr = window.devicePixelRatio || 1;

    c.width = w * dpr;
    c.height = h * dpr;

    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);

    const vals = transactions
        .slice(0, 12)
        .reverse()
        .map(x => x.risk_score);

    const pad = 30;
    const cw = w - 2 * pad;
    const ch = h - 55;

    ctx.strokeStyle = "#2a3954";

    for (let i = 0; i < 5; i++) {
        let y = 15 + ch * i / 4;

        ctx.beginPath();
        ctx.moveTo(pad, y);
        ctx.lineTo(w - pad, y);
        ctx.stroke();
    }

    if (!vals.length) {
        ctx.fillStyle = "#91a2bf";
        ctx.fillText(
            "Upload transactions to see scores",
            pad,
            h / 2
        );
        return;
    }

    const pts = vals.map((v, i) => ({
        x: pad + (
            vals.length === 1
                ? cw / 2
                : cw * i / (vals.length - 1)
        ),
        y: 15 + ch - (v / 100) * ch
    }));

    ctx.beginPath();

    pts.forEach((p, i) => {
        if (i) {
            ctx.lineTo(p.x, p.y);
        } else {
            ctx.moveTo(p.x, p.y);
        }
    });

    ctx.strokeStyle = "#8295ff";
    ctx.lineWidth = 2.5;
    ctx.stroke();

    pts.forEach(p => {
        ctx.beginPath();
        ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
        ctx.fillStyle = "#3bd9b4";
        ctx.fill();
    });

    ctx.fillStyle = "#91a2bf";
    ctx.font = "10px DM Sans";

    ctx.fillText("0", 8, 15 + ch);
    ctx.fillText("100", 4, 22);
}


// --------------------------------
// DASHBOARD CHARTS
// --------------------------------

function drawCharts() {
    if (!dashboardData) return;

    const vals = [
        dashboardData.high,
        dashboardData.medium,
        dashboardData.low
    ];

    drawBarChart(
        "riskChart",
        ["HIGH", "MEDIUM", "LOW"],
        vals,
        ["#ff667e", "#f4bd5c", "#3bd9b4"]
    );

    drawBarChart(
        "analyticsChart",
        ["HIGH", "MEDIUM", "LOW"],
        vals,
        ["#ff667e", "#f4bd5c", "#3bd9b4"]
    );

    drawScoreChart();
}


// --------------------------------
// REFRESH DASHBOARD DATA
// --------------------------------

async function refreshAll() {
    try {
        const d = await api("/api/dashboard");

        dashboardData = d;

        document.getElementById("total").textContent = d.total;
        document.getElementById("high").textContent = d.high;
        document.getElementById("medium").textContent = d.medium;
        document.getElementById("runCount").textContent = d.runs.length;

        document.getElementById("recentRows").innerHTML =
            d.transactions.length
                ? d.transactions
                    .slice(0, 8)
                    .map(recentRow)
                    .join("")
                : `
                    <tr>
                        <td colspan="7" class="empty">
                            No transactions yet. Run the pipeline.
                        </td>
                    </tr>
                `;

        const runMarkup = d.runs.length
            ? d.runs.map(r => `
                <tr>
                    <td>${escapeHtml(r.batch_id)}</td>
                    <td>${escapeHtml(r.source)}</td>
                    <td>${r.input_rows}</td>
                    <td>${r.valid_rows}</td>
                    <td>${r.rejected_rows}</td>
                    <td>${r.duplicates}</td>
                    <td>${r.flagged}</td>
                    <td>${badge(
                        r.status === "SUCCESS" ? "LOW" : "HIGH"
                    )}</td>
                </tr>
            `).join("")
            : `
                <tr>
                    <td colspan="8" class="empty">
                        No pipeline runs yet.
                    </td>
                </tr>
            `;

        ["pipelineRows", "automationRows"].forEach(id => {
            const el = document.getElementById(id);

            if (el) {
                el.innerHTML = runMarkup;
            }
        });

        const latest = d.runs[0];

        const sum = document.getElementById("pipelineSummary");

        if (sum) {
            sum.innerHTML = latest
                ? `
                    <div class="summary-item">
                        <b>${escapeHtml(latest.status)} · ${escapeHtml(latest.batch_id)}</b>
                        <small>Source: ${escapeHtml(latest.source)}</small>
                    </div>
                    <div class="summary-item">
                        <b>
                            ${latest.valid_rows} valid /
                            ${latest.input_rows} input records
                        </b>
                        <small>
                            ${latest.rejected_rows} rejected ·
                            ${latest.duplicates} duplicates ·
                            ${latest.flagged} risk-flagged
                        </small>
                    </div>
                `
                : `
                    <div class="empty">
                        No pipeline runs yet. Upload a CSV in Data pipeline.
                    </div>
                `;
        }

        transactions = await api("/api/transactions");

        renderTransactions();
        drawCharts();

    } catch (e) {
        console.error("Dashboard refresh:", e);
    }
}


// --------------------------------
// CSV UPLOAD AND ETL EXECUTION
// --------------------------------

async function uploadCsv() {
    const f = document.getElementById("file").files[0];
    const msg = document.getElementById("uploadMessage");

    if (!f) {
        msg.textContent = "Please choose a CSV file first.";
        return;
    }

    const fd = new FormData();

    fd.append("file", f);

    msg.textContent =
        "Pipeline running: Bronze → Silver → Gold…";

    try {
        const d = await api("/api/upload", {
            method: "POST",
            body: fd
        });

        msg.textContent =
            `${d.status} · Batch ${d.batch_id}: ` +
            `${d.input_rows} input, ` +
            `${d.valid_rows} valid, ` +
            `${d.rejected_rows} rejected, ` +
            `${d.duplicates} duplicates, ` +
            `${d.flagged} flagged.`;

        await refreshAll();

    } catch (e) {
        msg.textContent = "Pipeline error: " + e.message;
    }
}


// ================================================
// NORMETRIC CONVERSATIONAL AI ASSISTANT
// ================================================

let chatHistory = [];
let chatBusy = false;


// --------------------------------
// SAFE MARKDOWN RESPONSE FORMATTER
// --------------------------------

function formatAssistantMessage(markdown) {
    const lines = String(markdown ?? "").split(/\r?\n/);

    let html = "";
    let paragraph = [];
    let listType = null;

    function formatInline(value) {
        return escapeHtml(value)
            .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
            .replace(/\*([^*]+)\*/g, "<em>$1</em>")
            .replace(/`([^`]+)`/g, "<code>$1</code>");
    }

    function flushParagraph() {
        if (paragraph.length) {
            html += `<p>${paragraph.map(formatInline).join("<br>")}</p>`;
            paragraph = [];
        }
    }

    function closeList() {
        if (listType) {
            html += listType === "ul" ? "</ul>" : "</ol>";
            listType = null;
        }
    }

    for (const rawLine of lines) {
        const line = rawLine.trim();

        if (!line) {
            flushParagraph();
            closeList();
            continue;
        }

        const heading = line.match(/^(#{1,4})\s+(.+)$/);

        if (heading) {
            flushParagraph();
            closeList();

            const level = Math.min(heading[1].length + 1, 4);

            html += `<h${level}>${formatInline(heading[2])}</h${level}>`;
            continue;
        }

        const bullet = line.match(/^[-*•]\s+(.+)$/);
        const numbered = line.match(/^\d+[.)]\s+(.+)$/);

        if (bullet || numbered) {
            flushParagraph();

            const nextType = bullet ? "ul" : "ol";

            if (listType !== nextType) {
                closeList();
                html += `<${nextType}>`;
                listType = nextType;
            }

            html += `<li>${formatInline(
                bullet ? bullet[1] : numbered[1]
            )}</li>`;

            continue;
        }

        closeList();
        paragraph.push(line);
    }

    flushParagraph();
    closeList();

    return html;
}


// --------------------------------
// DISPLAY CHAT MESSAGE
// --------------------------------

function addChatMessage(role, text, typing = false) {
    const container = document.getElementById("chatMessages");

    if (!container) return null;

    const row = document.createElement("div");

    row.className =
        `chat-message ${role === "user" ? "user-message" : "assistant-message"}`;

    if (typing) {
        row.classList.add("typing");
    }

    const avatar = document.createElement("div");
    avatar.className = "chat-avatar";
    avatar.textContent = role === "user" ? "You" : "N";

    const bubble = document.createElement("div");
    bubble.className = "chat-bubble";

    if (role === "assistant" && !typing) {
        bubble.innerHTML = formatAssistantMessage(text);
    } else {
        bubble.textContent = text;
    }

    row.append(avatar, bubble);
    container.appendChild(row);

    container.scrollTop = container.scrollHeight;

    return row;
}


// --------------------------------
// CHAT SUGGESTION BUTTONS
// --------------------------------

function useChatPrompt(prompt) {
    const input = document.getElementById("chatInput");

    if (!input) return;

    input.value = prompt;
    input.focus();

    sendChatMessage();
}


// --------------------------------
// SEND MESSAGE TO AI BACKEND
// --------------------------------

async function sendChatMessage() {
    const input = document.getElementById("chatInput");
    const button = document.getElementById("chatSendButton");
    const status = document.getElementById("chatStatus");

    if (!input || chatBusy) return;

    const question = input.value.trim();

    if (!question) {
        input.focus();
        return;
    }

    if (question.length > 1000) {
        status.textContent =
            "Please keep your question under 1,000 characters.";
        return;
    }

    chatBusy = true;
    button.disabled = true;
    button.textContent = "Thinking…";

    addChatMessage("user", question);

    input.value = "";

    const typingRow = addChatMessage(
        "assistant",
        "NORMETRIC is analysing your data…",
        true
    );

    status.textContent = "Connecting to the AI assistant…";

    try {
        const result = await api("/api/ai/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                question: question,
                history: chatHistory
            })
        });

        const answer =
            result.answer ||
            "The AI assistant returned an empty response.";

        if (typingRow) {
            typingRow.remove();
        }

        addChatMessage("assistant", answer);

        chatHistory.push(
            { role: "user", content: question },
            { role: "assistant", content: answer }
        );

        chatHistory = chatHistory.slice(-6);

        status.textContent =
            "Response generated from the current NORMETRIC database context.";

    } catch (error) {
        if (typingRow) {
            typingRow.remove();
        }

        addChatMessage(
            "assistant",
            `I couldn't process that request. ${error.message}`
        );

        status.textContent =
            "AI assistant unavailable. Please try again.";

    } finally {
        chatBusy = false;
        button.disabled = false;
        button.textContent = "Send ↑";
        input.focus();
    }
}


// --------------------------------
// CHAT FORM EVENTS
// --------------------------------

const chatForm = document.getElementById("chatForm");

if (chatForm) {
    chatForm.addEventListener("submit", event => {
        event.preventDefault();
        sendChatMessage();
    });
}

const chatInput = document.getElementById("chatInput");

if (chatInput) {
    chatInput.addEventListener("keydown", event => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            sendChatMessage();
        }
    });
}


// --------------------------------
// INITIALIZATION
// --------------------------------

window.addEventListener("resize", () => drawCharts());

const initial = location.hash.replace("#", "");

showPage(
    [
        "dashboard",
        "pipeline",
        "automation",
        "transactions",
        "analytics",
        "assistant"
    ].includes(initial)
        ? initial
        : "home"
);

refreshAll();

setInterval(refreshAll, 10000);