(() => {
  const PERSONA = { MECHANICAL: "机械", SECRET: "偷偷活动" };
  const PRESENCE = { PRESENT: "有人", ABSENT: "无人", UNKNOWN: "未知" };
  const STATE_POLL_MS = 500;
  const EVENT_POLL_MS = 1000;
  const STALE_MS = 2000;

  const $ = (id) => document.getElementById(id);
  const connectionLabel = $("connection-label");
  const modeBadge = $("mode-badge");
  const staleLabel = $("stale-label");
  const personaLabel = $("persona-label");
  const presenceLabel = $("presence-label");
  const safetyLabel = $("safety-label");
  const sceneLabel = $("scene-label");
  const feedbackLabel = $("feedback-label");
  const eventList = $("event-list");
  const eventEmpty = $("event-empty");
  const memoryGeneration = $("memory-generation");
  const memoryList = $("memory-list");

  let lastStateAt = 0;
  let eventCursor = "";

  function setText(el, value) {
    el.textContent = value == null ? "" : String(value);
  }

  function markStale() {
    if (Date.now() - lastStateAt > STALE_MS) {
      staleLabel.hidden = false;
      setText(staleLabel, "失联 / 陈旧");
    }
  }

  async function pollState() {
    // Poll /api/v1/state every 500ms for a lightweight snapshot. No control WebSocket.
    try {
      const response = await fetch("/api/v1/state");
      if (!response.ok) {
        markStale();
        return;
      }
      const state = await response.json();
      lastStateAt = Date.now();
      staleLabel.hidden = Boolean(state.stale) === false;
      if (state.stale) setText(staleLabel, "陈旧");
      const connection = state.connection === "offline" ? "离线" : "模拟输入";
      setText(connectionLabel, connection);
      setText(modeBadge, state.mode === "sim" ? "模拟输入" : String(state.mode || "未知"));
      let persona = PERSONA[state.persona] || state.persona || "机械";
      if (state.paused) persona += " · 已暂停";
      setText(personaLabel, persona);
      setText(presenceLabel, PRESENCE[state.presence] || state.presence || "未知");
      setText(safetyLabel, state.safety || "unknown");
      setText(sceneLabel, state.scene_id || "无");
    } catch (_err) {
      markStale();
    }
  }

  async function pollEvents() {
    const query = new URLSearchParams({ limit: "50" });
    if (eventCursor !== "") query.set("cursor", String(eventCursor));
    try {
      const response = await fetch(`/api/v1/events?${query.toString()}`);
      if (!response.ok) return;
      const body = await response.json();
      const events = Array.isArray(body.events) ? body.events : [];
      if (body.cursor != null) eventCursor = String(body.cursor);
      for (const event of events) {
        const item = document.createElement("li");
        const type = document.createElement("strong");
        setText(type, event.type || "event");
        item.appendChild(type);
        const bits = [];
        if (event.presence) bits.push(String(event.presence));
        if (event.text) bits.push(String(event.text));
        if (event.simulated) bits.push("模拟");
        if (bits.length) {
          item.appendChild(document.createTextNode(" · " + bits.join(" · ")));
        }
        eventList.appendChild(item);
      }
      const hasItems = eventList.children.length > 0;
      eventEmpty.hidden = hasItems;
      while (eventList.children.length > 500) {
        eventList.removeChild(eventList.firstChild);
      }
    } catch (_err) {
      /* keep last rendered events */
    }
  }

  async function pollMemory() {
    try {
      const response = await fetch("/api/v1/memory");
      if (!response.ok) return;
      const body = await response.json();
      setText(memoryGeneration, body.generation);
      memoryList.replaceChildren();
      const items = Array.isArray(body.items) ? body.items : [];
      for (const item of items) {
        const li = document.createElement("li");
        setText(li, typeof item === "string" ? item : JSON.stringify(item));
        memoryList.appendChild(li);
      }
    } catch (_err) {
      /* ignore transient memory poll errors */
    }
  }

  async function postJson(url, body) {
    const response = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    return response;
  }

  $("btn-stop").addEventListener("click", async () => {
    const response = await fetch("/api/v1/control/stop", { method: "POST" });
    const body = await response.json().catch(() => ({}));
    setText(
      feedbackLabel,
      `已请求暂停（request_id=${body.request_id || "?"}），未宣称物理停稳`,
    );
    pollState();
    pollEvents();
  });

  $("btn-clear-memory").addEventListener("click", async () => {
    if (!window.confirm("确认清空角色记忆？此操作不可从本页恢复。")) return;
    const response = await fetch("/api/v1/memory", { method: "DELETE" });
    const body = await response.json().catch(() => ({}));
    setText(feedbackLabel, `记忆已请求清空，generation=${body.generation || "?"}`);
    pollMemory();
    pollEvents();
  });

  async function sendPresence(presence) {
    await postJson("/api/v1/rehearsal/events", { type: "presence", presence });
    setText(feedbackLabel, `已发送模拟人员事件：${presence}`);
    pollState();
    pollEvents();
  }

  $("btn-present").addEventListener("click", () => sendPresence("PRESENT"));
  $("btn-absent").addEventListener("click", () => sendPresence("ABSENT"));
  $("btn-unknown").addEventListener("click", () => sendPresence("UNKNOWN"));

  pollState();
  pollEvents();
  pollMemory();
  setInterval(pollState, STATE_POLL_MS);
  setInterval(pollEvents, EVENT_POLL_MS);
  setInterval(pollMemory, 2000);
  setInterval(markStale, 500);
})();
