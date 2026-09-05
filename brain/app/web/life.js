(() => {
  const $ = (id) => document.getElementById(id);

  function setText(el, value) {
    el.textContent = value == null ? "" : String(value);
  }

  function fillOrigin(origin) {
    $("origin-name").value = origin.name || "";
    $("origin-backstory").value = origin.backstory || "";
    $("origin-alone").value = origin.alone || "";
    $("origin-public").value = origin.public || "";
    $("origin-secret").value = origin.secret || "";
  }

  function readOrigin() {
    return {
      name: $("origin-name").value,
      backstory: $("origin-backstory").value,
      alone: $("origin-alone").value,
      public: $("origin-public").value,
      secret: $("origin-secret").value,
    };
  }

  function appendChat(role, text, source) {
    const item = document.createElement("li");
    const who = document.createElement("strong");
    setText(who, role);
    item.appendChild(who);
    item.appendChild(document.createTextNode(" " + text));
    if (source) {
      const tag = document.createElement("span");
      tag.className = "note";
      setText(tag, " · " + source);
      item.appendChild(tag);
    }
    $("chat-log").appendChild(item);
    if (role === "牛来" && window.speechSynthesis && text) {
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(text);
      utter.lang = "zh-CN";
      window.speechSynthesis.speak(utter);
    }
  }

  async function loadOrigin() {
    const response = await fetch("/api/v1/origin");
    if (!response.ok) return;
    const body = await response.json();
    fillOrigin(body.origin || {});
    setText(
      $("llm-badge"),
      body.llm ? "大脑：已接大模型" : "大脑：未配置密钥，先用身世模板（不是真闲聊）",
    );
  }

  $("origin-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const response = await fetch("/api/v1/origin", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(readOrigin()),
    });
    if (!response.ok) return;
    const body = await response.json();
    fillOrigin(body.origin || {});
    setText($("llm-badge"), (body.llm ? "已保存 · 大模型" : "已保存 · 模板") + "在线");
  });

  $("chat-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = $("chat-text").value.trim();
    const presence = $("chat-presence").value;
    if (text) appendChat("你", text);
    $("chat-text").value = "";
    const response = await fetch("/api/v1/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, presence }),
    });
    if (!response.ok) return;
    const body = await response.json();
    appendChat("牛来", body.reply || "", body.source);
  });

  loadOrigin();
})();
