// app.js — SmartGarden WebSocket Client (Vanilla JS)
// ════════════════════════════════════════════════════

const API_KEY = "smartgarden-secret-key-2026";
const WS_URL = `ws://${location.host}/ws`;

// ── DOM refs ───────────────────────────────────────
const nodeSelect = document.getElementById("nodeSelect");
const statusBadge = document.getElementById("statusBadge");
const btnMode = document.getElementById("btnMode");
const wsStatus = document.getElementById("wsStatus");
const cameraImg = document.getElementById("cameraImg");
const cameraPlaceholder = document.getElementById("cameraPlaceholder");
const valTemp = document.getElementById("valTemp");
const valHum = document.getElementById("valHum");
const barSoil = document.getElementById("barSoil");
const valLight = document.getElementById("valLight");
const aiLog = document.getElementById("aiLog");
const btnPump = document.getElementById("btnPump");
const btnFan = document.getElementById("btnFan");
const btnLight = document.getElementById("btnLight");

// ── State ──────────────────────────────────────────
let currentMode = "auto";
let ws = null;

// ── WebSocket ──────────────────────────────────────
function connectWS() {
  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    wsStatus.textContent = "🟢 Đã kết nối";
    wsStatus.className = "text-lg font-bold text-green-500";
    ws.send(JSON.stringify({ type: "subscribe", node_id: "all" }));
  };

  ws.onclose = () => {
    wsStatus.textContent = "🔴 Mất kết nối — đang thử lại...";
    wsStatus.className = "text-lg font-bold text-red-500";
    setTimeout(connectWS, 3000);
  };

  ws.onerror = () => {
    ws.close();
  };

  ws.onmessage = (event) => {
    let msg;
    try { msg = JSON.parse(event.data); } catch { return; }
    handleMessage(msg);
  };
}

function handleMessage(msg) {
  switch (msg.type) {
    case "init_state":
      if (Array.isArray(msg.data) && msg.data.length > 0) {
        updateUI(msg.data[0]);
      }
      break;

    case "telemetry_update":
      updateSensors(msg.data);
      updateImage(msg.data.image_url);
      updateAILog(msg.data.ai_reasoning, msg.data.action_code);
      if (msg.data.device_states) updateDeviceButtons(msg.data.device_states);
      setStatus("online");
      break;

    case "device_update":
      if (msg.device_states) updateDeviceButtons(msg.device_states);
      break;

    case "mode_update":
      currentMode = msg.mode;
      refreshModeUI();
      break;

    case "node_status":
      setStatus(msg.status);
      break;
  }
}

// ── UI updaters ────────────────────────────────────
function updateUI(state) {
  if (!state) return;
  valTemp.textContent = state.temperature != null ? `${state.temperature} °C` : "-- °C";
  valHum.textContent = state.humidity != null ? `${state.humidity} %` : "-- %";
  updateSoilBar(state.avg_soil || 0);
  valLight.textContent = state.light_lux != null ? `${state.light_lux} Lux` : "-- Lux";
  if (state.image_url) updateImage(state.image_url);
  if (state.ai_reasoning) updateAILog(state.ai_reasoning, state.action_code);
  if (state.device_states) updateDeviceButtons(state.device_states);
  if (state.mode) { currentMode = state.mode; refreshModeUI(); }
  setStatus(state.status || "offline");
}

function updateSensors(data) {
  valTemp.textContent = `${data.temperature} °C`;
  valHum.textContent = `${data.humidity} %`;
  updateSoilBar(data.avg_soil || 0);
  valLight.textContent = `${data.light_lux} Lux`;
}

function updateSoilBar(value) {
  const pct = Math.min(100, Math.max(0, Math.round(value)));
  barSoil.style.width = pct + "%";
  barSoil.textContent = pct + "%";
}

function updateImage(url) {
  if (!url) return;
  cameraImg.src = url;
  cameraImg.classList.remove("hidden");
  cameraPlaceholder.classList.add("hidden");
}

function updateAILog(reasoning, actionCode) {
  if (!reasoning) return;
  const time = new Date().toLocaleTimeString("vi-VN");
  const actionMap = { 0: "Giữ nguyên", 1: "Bật bơm", 2: "Bật quạt", 3: "Bơm + Quạt", 5: "Bật đèn" };
  const actionText = actionMap[actionCode] || `Code ${actionCode}`;
  const p = document.createElement("p");
  p.innerHTML = `<span class="text-gray-400">[${time}]</span> <b class="text-blue-600">${actionText}</b> — ${reasoning}`;
  aiLog.appendChild(p);
  aiLog.scrollTop = aiLog.scrollHeight;

  // Xóa placeholder
  const placeholder = aiLog.querySelector(".italic");
  if (placeholder) placeholder.remove();
}

function updateDeviceButtons(states) {
  setDeviceBtn(btnPump, states.pump, "💦 BƠM NƯỚC", "bg-blue-500", "bg-gray-400");
  setDeviceBtn(btnFan, states.fan, "🌀 QUẠT GIÓ", "bg-yellow-500", "bg-gray-400");
  setDeviceBtn(btnLight, states.light, "💡 ĐÈN", "bg-green-500", "bg-gray-400");
}

function setDeviceBtn(btn, isOn, label, onClass, offClass) {
  btn.textContent = `${label}: ${isOn ? "ĐANG BẬT" : "TẮT"}`;
  btn.classList.remove(onClass, offClass);
  btn.classList.add(isOn ? onClass : offClass);
}

function setStatus(status) {
  if (status === "online") {
    statusBadge.textContent = "ONLINE";
    statusBadge.className = "px-3 py-1 rounded-full text-xs font-bold bg-green-100 text-green-700";
  } else {
    statusBadge.textContent = "OFFLINE";
    statusBadge.className = "px-3 py-1 rounded-full text-xs font-bold bg-gray-200 text-gray-600";
  }
}

// ── Mode toggle ────────────────────────────────────
function refreshModeUI() {
  if (currentMode === "auto") {
    btnMode.textContent = "TỰ ĐỘNG";
    btnMode.className = "px-4 py-2 rounded-lg text-sm font-bold bg-green-500 text-white";
    document.querySelectorAll(".device-btn").forEach(b => b.disabled = true);
  } else {
    btnMode.textContent = "THỦ CÔNG";
    btnMode.className = "px-4 py-2 rounded-lg text-sm font-bold bg-orange-500 text-white";
    document.querySelectorAll(".device-btn").forEach(b => b.disabled = false);
  }
}

btnMode.addEventListener("click", () => {
  const newMode = currentMode === "auto" ? "manual" : "auto";
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      type: "set_mode",
      api_key: API_KEY,
      node_id: parseInt(nodeSelect.value),
      mode: newMode
    }));
  }
});

// ── Device buttons (Manual mode) ───────────────────
function getActionCodeForDevice(device, currentlyOn) {
  // Nếu đang bật → tắt (action 0), nếu đang tắt → bật device tương ứng
  if (currentlyOn) return 0;
  const map = { pump: 1, fan: 2, light: 5 };
  return map[device] || 0;
}

document.querySelectorAll(".device-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    if (currentMode === "auto") return;
    const device = btn.dataset.device;
    const isOn = btn.textContent.includes("ĐANG BẬT");
    const actionCode = getActionCodeForDevice(device, isOn);

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: "manual_action",
        api_key: API_KEY,
        node_id: parseInt(nodeSelect.value),
        action_type: actionCode
      }));
    }
  });
});

// ── Init ───────────────────────────────────────────
refreshModeUI();
connectWS();
