from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import json
import os
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "shupl_campus_qa_secret_key"

PASSWORD = "12345"

# ============ 大模型配置（从环境变量读取） ============
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
MODEL_NAME = "deepseek-chat"
# ===================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_FILE = os.path.join(BASE_DIR, "knowledge.json")


def load_knowledge():
    if not os.path.exists(KNOWLEDGE_FILE):
        return []
    try:
        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("读取失败:", e)
        return []


def save_knowledge(data):
    with open(KNOWLEDGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def retrieve(question, knowledge, top_k=8):
    question = question.lower()
    scored = []
    for item in knowledge:
        if item.get("type") == "weekly":
            continue
        score = 0
        for kw in item.get("keywords", []):
            if kw.lower() in question:
                score += len(kw) * 3
        for kw in item.get("keywords", []):
            for part in kw:
                if part.strip() and part in question:
                    score += 1
        answer = item.get("answer", "").lower()
        for part in question:
            if part.strip() and part in answer:
                score += 0.5
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:top_k]]


def ask_llm(system_prompt, user_prompt):
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.3,
        "stream": False
    }
    try:
        resp = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=30)
        data = resp.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        print("大模型返回异常:", data)
        return "抱歉，智能助手暂时无法回答，请稍后再试。"
    except Exception as e:
        print("调用失败:", e)
        return "抱歉，智能助手暂时无法连接，请稍后再试。"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"answer": "请输入问题。"})

    knowledge = load_knowledge()
    contexts = retrieve(question, knowledge)

    if contexts:
        context_text = "\n\n".join(
            [f"【资料{i+1}】关键词：{','.join(c['keywords'])}\n内容：{c['answer']}"
             for i, c in enumerate(contexts)]
        )
    else:
        context_text = "（没有找到相关资料）"

    system_prompt = (
        "你是上海政法学院的校园智能问答助手。请根据下面提供的校园资料回答学生的问题。"
        "如果资料中有相关内容，请基于资料回答，语言自然、友好、简洁。"
        "如果资料中没有相关内容，请如实告诉学生没有找到，并建议他咨询相关部门。"
        "不要编造资料中没有的信息。"
    )
    user_prompt = f"校园资料：\n{context_text}\n\n学生问题：{question}"

    answer = ask_llm(system_prompt, user_prompt)
    return jsonify({"answer": answer})


@app.route("/api/weekly", methods=["POST"])
def weekly():
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    knowledge = load_knowledge()
    week_events = []
    for item in knowledge:
        if item.get("type") != "weekly":
            continue
        d = item.get("date", "")
        if not d:
            continue
        try:
            item_date = datetime.strptime(d, "%Y-%m-%d").date()
        except Exception:
            continue
        if monday <= item_date <= sunday:
            week_events.append(item)

    if not week_events:
        return jsonify({
            "answer": f"📰 **本周大事报**（{monday} 至 {sunday}）\n\n本周暂无录入的校园大事。\n\n如需了解最新资讯，请关注“青春上政”公众号，或在后台录入本周事件。"
        })

    week_events.sort(key=lambda x: x.get("date", ""))
    events_text = "\n\n".join(
        [f"【{e.get('date')}】{e['answer']}" for e in week_events]
    )

    system_prompt = (
        "你是上海政法学院的校园资讯编辑。请根据下面提供的本周事件，整理成一份清晰、友好的“本周大事报”。"
        "要求：1. 按日期或重要性组织；2. 语言简洁；3. 用有序列表或分段呈现；4. 不要编造未提供的信息。"
    )
    user_prompt = f"本周（{monday} 至 {sunday}）校园事件：\n{events_text}\n\n请整理成本周大事报。"

    answer = ask_llm(system_prompt, user_prompt)
    header = f"📰 **本周大事报**（{monday} 至 {sunday}）\n\n"
    return jsonify({"answer": header + answer})


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        pwd = request.form.get("password", "")
        if pwd == PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin"))
        return render_template("admin_login.html", error="密码错误")
    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))


@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    knowledge = load_knowledge()
    return render_template("admin.html", knowledge=knowledge)


@app.route("/admin/add", methods=["POST"])
def admin_add():
    if not session.get("admin"):
        return jsonify({"ok": False, "msg": "未登录"})
    data = request.get_json()
    keywords = [k.strip() for k in data.get("keywords", "").split(",") if k.strip()]
    answer = data.get("answer", "").strip()
    date = data.get("date", "").strip()
    item_type = data.get("type", "normal").strip()
    if not answer:
        return jsonify({"ok": False, "msg": "答案不能为空"})
    if item_type == "normal" and not keywords:
        return jsonify({"ok": False, "msg": "普通问答的关键词不能为空"})
    knowledge = load_knowledge()
    item = {"keywords": keywords, "answer": answer, "type": item_type}
    if date:
        item["date"] = date
    knowledge.append(item)
    save_knowledge(knowledge)
    return jsonify({"ok": True})


@app.route("/admin/update", methods=["POST"])
def admin_update():
    if not session.get("admin"):
        return jsonify({"ok": False, "msg": "未登录"})
    data = request.get_json()
    idx = data.get("index")
    keywords = [k.strip() for k in data.get("keywords", "").split(",") if k.strip()]
    answer = data.get("answer", "").strip()
    date = data.get("date", "").strip()
    item_type = data.get("type", "normal").strip()
    knowledge = load_knowledge()
    if idx is None or idx < 0 or idx >= len(knowledge):
        return jsonify({"ok": False, "msg": "索引错误"})
    item = {"keywords": keywords, "answer": answer, "type": item_type}
    if date:
        item["date"] = date
    knowledge[idx] = item
    save_knowledge(knowledge)
    return jsonify({"ok": True})


@app.route("/admin/delete", methods=["POST"])
def admin_delete():
    if not session.get("admin"):
        return jsonify({"ok": False, "msg": "未登录"})
    data = request.get_json()
    idx = data.get("index")
    knowledge = load_knowledge()
    if idx is None or idx < 0 or idx >= len(knowledge):
        return jsonify({"ok": False, "msg": "索引错误"})
    knowledge.pop(idx)
    save_knowledge(knowledge)
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)