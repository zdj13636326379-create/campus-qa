const chatBox = document.getElementById("chatBox");
const input = document.getElementById("questionInput");
const sendBtn = document.getElementById("sendBtn");
let isLoading = false;

function addMessage(text, type) {
  const msg = document.createElement("div");
  msg.className = "message " + type;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = type === "bot" ? "🤖" : "👤";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;

  msg.appendChild(avatar);
  msg.appendChild(bubble);
  chatBox.appendChild(msg);
  chatBox.scrollTop = chatBox.scrollHeight;
  return msg;
}

function addLoading() {
  const msg = document.createElement("div");
  msg.className = "message bot";
  msg.id = "loadingMsg";

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = "🤖";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = '<div class="typing"><span></span><span></span><span></span></div>';

  msg.appendChild(avatar);
  msg.appendChild(bubble);
  chatBox.appendChild(msg);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function removeLoading() {
  const el = document.getElementById("loadingMsg");
  if (el) el.remove();
}

async function sendQuestion() {
  if (isLoading) return;

  const question = input.value.trim();
  if (!question) return;

  addMessage(question, "user");
  input.value = "";
  isLoading = true;
  sendBtn.disabled = true;
  sendBtn.textContent = "思考中…";

  addLoading();

  try {
    const res = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question })
    });
    const data = await res.json();
    removeLoading();
    addMessage(data.answer, "bot");
  } catch (e) {
    removeLoading();
    addMessage("网络出错了，请稍后再试。", "bot");
  } finally {
    isLoading = false;
    sendBtn.disabled = false;
    sendBtn.textContent = "发送";
  }
}

function quickAsk(q) {
  if (isLoading) return;
  input.value = q;
  sendQuestion();
}

async function askWeekly() {
  if (isLoading) return;
  addMessage("本周大事报", "user");
  isLoading = true;
  sendBtn.disabled = true;
  sendBtn.textContent = "思考中…";
  addLoading();

  try {
    const res = await fetch("/api/weekly", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({})
    });
    const data = await res.json();
    removeLoading();
    addMessage(data.answer, "bot");
  } catch (e) {
    removeLoading();
    addMessage("网络出错了，请稍后再试。", "bot");
  } finally {
    isLoading = false;
    sendBtn.disabled = false;
    sendBtn.textContent = "发送";
  }
}

input.addEventListener("keydown", e => {
  if (e.key === "Enter") sendQuestion();
});