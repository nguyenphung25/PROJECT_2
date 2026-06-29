const API_BASE = "http://localhost:5000";

let currentPendingId = null;
let currentAction = null;

let lastEntryKey = "";
let lastExitKey = "";

let entryResetTimer = null;
let exitResetTimer = null;

let historySearchQuery = "";
let historyStatusFilter = "all";
let allHistoryItems = [];
let showAllHistory = false;

const RESET_DELAY = 6000;

// Cooldown sau khi reset: bỏ qua polling 1 chu kỳ để tránh
// polling kéo lại event cũ từ backend ngay sau khi reset UI.
let resetCooldownUntil = 0;

/* =========================
   CLOCK
========================= */

function updateClock() {
  const now = new Date();

  const hours = String(now.getHours()).padStart(2, "0");
  const minutes = String(now.getMinutes()).padStart(2, "0");
  const seconds = String(now.getSeconds()).padStart(2, "0");

  const day = String(now.getDate()).padStart(2, "0");
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const year = now.getFullYear();

  const clockElement = document.getElementById("realTimeClock");

  if (clockElement) {
    clockElement.textContent = `${hours}:${minutes}:${seconds} - ${day}/${month}/${year}`;
  }
}

function getCurrentTimeString() {
  const now = new Date();

  const hours = String(now.getHours()).padStart(2, "0");
  const minutes = String(now.getMinutes()).padStart(2, "0");
  const seconds = String(now.getSeconds()).padStart(2, "0");

  const day = String(now.getDate()).padStart(2, "0");
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const year = now.getFullYear();

  return `${hours}:${minutes}:${seconds} - ${day}/${month}/${year}`;
}

/* =========================
   CAMERA HELPERS
========================= */

function buildImageUrl(imagePath) {
  if (!imagePath) return "";

  if (imagePath.startsWith("http://") || imagePath.startsWith("https://")) {
    return imagePath;
  }

  return `${API_BASE}/${imagePath.replaceAll("\\", "/")}`;
}

function showLiveCamera(action) {
  const cameraBox = document.getElementById(
    action === "entry" ? "entryCameraBox" : "exitCameraBox",
  );

  const liveImage = document.getElementById(
    action === "entry" ? "entryLiveCamera" : "exitLiveCamera",
  );

  const capturedImage = document.getElementById(
    action === "entry" ? "entryCapturedImage" : "exitCapturedImage",
  );

  if (!cameraBox || !liveImage) return;

  if (capturedImage) {
    capturedImage.removeAttribute("src");
  }

  liveImage.src = `${API_BASE}/video_feed?t=${Date.now()}`;

  cameraBox.classList.remove("defaultCamera");
  cameraBox.classList.remove("showCaptured");
  cameraBox.classList.add("showLive");
}

function setCameraImage(action, imagePath) {
  const imageUrl = buildImageUrl(imagePath);

  if (!imageUrl) return;

  const cameraBox = document.getElementById(
    action === "entry" ? "entryCameraBox" : "exitCameraBox",
  );

  const liveImage = document.getElementById(
    action === "entry" ? "entryLiveCamera" : "exitLiveCamera",
  );

  const capturedImage = document.getElementById(
    action === "entry" ? "entryCapturedImage" : "exitCapturedImage",
  );

  if (!cameraBox || !capturedImage) return;

  if (liveImage) {
    liveImage.removeAttribute("src");
  }

  capturedImage.src = `${imageUrl}?t=${Date.now()}`;

  cameraBox.classList.remove("defaultCamera");
  cameraBox.classList.remove("showLive");
  cameraBox.classList.add("showCaptured");
}

function resetCameraUI(action) {
  const cameraBox = document.getElementById(
    action === "entry" ? "entryCameraBox" : "exitCameraBox",
  );

  const liveImage = document.getElementById(
    action === "entry" ? "entryLiveCamera" : "exitLiveCamera",
  );

  const capturedImage = document.getElementById(
    action === "entry" ? "entryCapturedImage" : "exitCapturedImage",
  );

  const plateBox = document.getElementById(
    action === "entry" ? "entryPlateBox" : "exitPlateBox",
  );

  if (liveImage) {
    liveImage.removeAttribute("src");
  }

  if (capturedImage) {
    capturedImage.removeAttribute("src");
  }

  if (cameraBox) {
    cameraBox.classList.remove("showLive");
    cameraBox.classList.remove("showCaptured");
    cameraBox.classList.add("defaultCamera");
  }

  if (plateBox) {
    plateBox.textContent = "--";
    plateBox.classList.remove("success", "error");
    plateBox.classList.add("waiting");
  }

  const ocrResult = document.getElementById(
    action === "entry" ? "entryOcrResult" : "exitOcrResult",
  );

  if (ocrResult) {
    ocrResult.textContent = action === "entry" ? "--" : "Đang chờ phương tiện...";
  }
}

function resetOtherCamera(action) {
  if (action === "entry") {
    resetCameraUI("exit");
  }

  if (action === "exit") {
    resetCameraUI("entry");
  }
}

function scheduleResetCamera(action) {
  if (action === "entry") {
    if (entryResetTimer) {
      clearTimeout(entryResetTimer);
    }

    entryResetTimer = setTimeout(() => {
      resetCameraUI("entry");
    }, RESET_DELAY);
  }

  if (action === "exit") {
    if (exitResetTimer) {
      clearTimeout(exitResetTimer);
    }

    exitResetTimer = setTimeout(() => {
      resetCameraUI("exit");
    }, RESET_DELAY);
  }
}

/* =========================
   PLATE UI
========================= */

function setPlateStatus(plateBox, status) {
  if (!plateBox) return;

  plateBox.classList.remove("success", "error", "waiting");

  if (status) {
    plateBox.classList.add(status);
  }
}

function updatePlateBox(action, plateText, message, allow) {
  const plateBox = document.getElementById(
    action === "entry" ? "entryPlateBox" : "exitPlateBox",
  );

  if (!plateBox) return;

  if (allow) {
    plateBox.textContent = plateText || "--";
    setPlateStatus(plateBox, "success");
  } else {
    plateBox.textContent = plateText || "KHÔNG NHẬN DIỆN";
    setPlateStatus(plateBox, "error");
  }

  const ocrResult = document.getElementById(
    action === "entry" ? "entryOcrResult" : "exitOcrResult",
  );

  if (ocrResult) {
    ocrResult.textContent = allow ? (plateText || message || "--") : (message || plateText || "--");
  }
}

function updateTransactionMessage(message, status = "") {
  const transactionMessage = document.getElementById("transactionMessage");

  if (!transactionMessage) return;

  transactionMessage.textContent = message || "Đang chờ phương tiện";
  transactionMessage.classList.remove("success", "error", "waiting");

  if (status) {
    transactionMessage.classList.add(status);
  }
}

/* =========================
   INFO UI
========================= */

function updateTransactionInfo(eventData) {
  if (!eventData || !eventData.action) return;

  // Chỉ cập nhật giờ vào/ra khi backend cho phép mở barrier
  if (!eventData.allow) return;

  const entryTime = document.getElementById("entryTime");
  const exitTime = document.getElementById("exitTime");

  const timeString = getCurrentTimeString();

  if (eventData.action === "entry" && entryTime) {
    entryTime.textContent = timeString;
  }

  if (eventData.action === "exit" && exitTime) {
    exitTime.textContent = timeString;
  }
}

function updateVehicleCount(count) {
  const vehicleCount = document.getElementById("vehicleCount");
  const historyCount = document.getElementById("vehicleCountHistory");

  if (vehicleCount) vehicleCount.textContent = String(count);
  if (historyCount) historyCount.textContent = `${count} xe đang trong bãi`;
}

async function syncVehicleCount() {
  try {
    const res = await fetch(`${API_BASE}/esp32/sync`);
    const data = await res.json();

    if (!data.success) {
      console.log("Không đồng bộ được số xe:", data.message);
      return;
    }

    const count = Number(data.vehicles_inside);

    if (Number.isNaN(count)) return;

    updateVehicleCount(count);
  } catch (error) {
    console.log("Lỗi đồng bộ số xe:", error.message);
  }
}

/* =========================
   MANUAL INPUT
========================= */

function showManualPanel(eventData) {
  currentPendingId = eventData.pending_id || null;
  currentAction = eventData.action || null;

  const panel = document.getElementById("manualPanel");
  const alertBox = document.getElementById("manualAlert");
  const input = document.getElementById("manualPlateInput");

  if (!panel || !alertBox || !input) return;

  const actionText = eventData.action === "entry" ? "xe vào" : "xe ra";

  alertBox.textContent =
    `${eventData.message || "Không nhận diện được biển số"} (${actionText}). ` +
    "Vui lòng nhập biển số thủ công.";

  input.value = eventData.plate_text || "";
  panel.classList.remove("hidden");
  input.focus();
}

function hideManualPanel() {
  const panel = document.getElementById("manualPanel");
  const input = document.getElementById("manualPlateInput");

  if (panel) {
    panel.classList.add("hidden");
  }

  if (input) {
    input.value = "";
  }

  currentPendingId = null;
  currentAction = null;
}

async function submitManualPlate() {
  const input = document.getElementById("manualPlateInput");

  if (!input) return;

  const plateText = input.value.trim();

  if (!plateText) {
    alert("Vui lòng nhập biển số xe");
    return;
  }

  if (!currentPendingId) {
    alert("Không có phiên nhận diện nào đang chờ nhập tay");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/manual/confirm`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        pending_id: currentPendingId,
        plate_text: plateText,
      }),
    });

    const data = await res.json();

    if (!data.success) {
      alert(data.message || "Biển số không hợp lệ");
      return;
    }

    if (data.event) {
      applyEventToUI(data.event, true);
    }

    hideManualPanel();
  } catch (error) {
    alert("Không gửi được biển số thủ công: " + error.message);
  }
}

/* =========================
   BACKEND STATE
========================= */

function getEventKey(eventData) {
  if (!eventData) return "";

  return [
    eventData.action || "",
    eventData.pending_id || "",
    eventData.detection_id || "",
    eventData.parking_session_id || "",
    eventData.image_url || "",
    eventData.image_path || "",
    eventData.plate_text || "",
    eventData.message || "",
    String(eventData.allow),
    String(eventData.manual_required),
    String(eventData.processing),
  ].join("|");
}

function applyEventToUI(eventData, forceUpdate = false) {
  if (!eventData || !eventData.action) return;

  const action = eventData.action;
  const eventKey = getEventKey(eventData);

  if (!forceUpdate) {
    if (action === "entry" && eventKey === lastEntryKey) return;
    if (action === "exit" && eventKey === lastExitKey) return;
  }

  if (action === "entry") {
    lastEntryKey = eventKey;
  }

  if (action === "exit") {
    lastExitKey = eventKey;
  }

  // ===== TRANG THAI DANG XU LY: bat live camera ngay lap tuc =====
  if (eventData.processing) {
    resetOtherCamera(action);
    showLiveCamera(action);
    updateTransactionMessage(eventData.message || "Đang nhận diện biển số...", "waiting");

    // Hien thi "Dang nhan dien..." tren plate box
    const plateBox = document.getElementById(
      action === "entry" ? "entryPlateBox" : "exitPlateBox",
    );
    if (plateBox) {
      plateBox.textContent = "ĐANG NHẬN DIỆN...";
      setPlateStatus(plateBox, "waiting");
    }

    const ocrResult = document.getElementById(
      action === "entry" ? "entryOcrResult" : "exitOcrResult",
    );
    if (ocrResult) ocrResult.textContent = "Đang quét...";

    return;  // Khong lam gi them cho den khi co ket qua
  }

  // ===== KET QUA CUOI CUNG: hien thi anh chup =====
  // Xe vào thì camera ra về mặc định, xe ra thì camera vào về mặc định
  resetOtherCamera(action);

  // Camera dung action hien thi anh chup
  setCameraImage(action, eventData.image_url || eventData.image_path);

  updatePlateBox(
    action,
    eventData.plate_text,
    eventData.message,
    eventData.allow,
  );
  updateTransactionMessage(
    eventData.message,
    eventData.allow ? "success" : "error",
  );

  updateTransactionInfo(eventData);
  loadHistoryTable();

  if (eventData.manual_required) {
    updateTransactionMessage(eventData.message, "error");
    showManualPanel(eventData);
  } else if (eventData.allow) {
    hideManualPanel();

    // Sau vài giây, camera vừa xử lý cũng quay về mặc định
    scheduleResetCamera(action);
  }
}

async function pollLatestState() {
  // Nếu vừa mới reset, bỏ qua poll này để backend có thời gian clear state
  if (Date.now() < resetCooldownUntil) return;

  try {
    const res = await fetch(`${API_BASE}/state/latest`);
    const data = await res.json();

    if (!data.success || !data.data) return;

    const entryEvent = data.data.entry;
    const exitEvent = data.data.exit;

    // Backend đã đảm bảo chỉ 1 trong 2 event có dữ liệu
    if (entryEvent) {
      applyEventToUI(entryEvent);
      return;
    }

    if (exitEvent) {
      applyEventToUI(exitEvent);
      return;
    }
  } catch (error) {
    console.log("Không lấy được trạng thái mới nhất:", error.message);
  }
}

/* =========================
   TEST BUTTONS
========================= */

async function triggerBackendAction(action) {
  const url = action === "entry" ? `${API_BASE}/entry` : `${API_BASE}/exit`;

  const button = document.querySelector(
    action === "entry" ? ".enterBtn" : ".exitBtn",
  );

  try {
    resetOtherCamera(action);
    showLiveCamera(action);

    const plateBox = document.getElementById(
      action === "entry" ? "entryPlateBox" : "exitPlateBox",
    );

    if (plateBox) {
      plateBox.textContent = "ĐANG QUÉT...";
      plateBox.classList.remove("success", "error");
      plateBox.classList.add("waiting");
    }

    const ocrResult = document.getElementById(
      action === "entry" ? "entryOcrResult" : "exitOcrResult",
    );
    if (ocrResult) ocrResult.textContent = "Đang quét...";

    if (button) {
      button.disabled = true;
      button.style.opacity = "0.75";
    }

    const res = await fetch(url);
    const data = await res.json();

    applyEventToUI(data, true);
  } catch (error) {
    alert(
      action === "entry"
        ? "Không gọi được API xe vào: " + error.message
        : "Không gọi được API xe ra: " + error.message,
    );
  } finally {
    if (button) {
      button.disabled = false;
      button.style.opacity = "1";
    }
  }
}

/* =========================
   RESET
========================= */

async function resetAllUI() {
  // Đặt cooldown TRƯỚC khi reset UI,
  // để polling không kéo lại event cũ trong lúc backend đang clear.
  resetCooldownUntil = Date.now() + 2000;

  resetCameraUI("entry");
  resetCameraUI("exit");

  hideManualPanel();

  const entryTime = document.getElementById("entryTime");
  const exitTime = document.getElementById("exitTime");
  const durationTime = document.getElementById("durationTime");
  const vehicleCount = document.getElementById("vehicleCount");

  if (entryTime) entryTime.textContent = "--:--:--";
  if (exitTime) exitTime.textContent = "--:--:--";
  if (durationTime) durationTime.textContent = "00:00:00";
  if (vehicleCount) vehicleCount.textContent = "0";
  updateTransactionMessage("Đang chờ phương tiện");

  lastEntryKey = "";
  lastExitKey = "";

  if (entryResetTimer) {
    clearTimeout(entryResetTimer);
    entryResetTimer = null;
  }

  if (exitResetTimer) {
    clearTimeout(exitResetTimer);
    exitResetTimer = null;
  }

  try {
    await fetch(`${API_BASE}/state/reset`, {
      method: "POST",
    });

    syncVehicleCount();
  } catch (error) {
    console.log("Không reset được backend:", error.message);
  }
}

/* =========================
   INIT
========================= */

document.addEventListener("DOMContentLoaded", () => {
  updateClock();
  setInterval(updateClock, 1000);

  resetCameraUI("entry");
  resetCameraUI("exit");

  syncVehicleCount();
  loadHistoryTable();
  setInterval(loadHistoryTable, 3000);
  setInterval(syncVehicleCount, 3000);
  pollLatestState();
  setInterval(pollLatestState, 1000);

  const manualSubmitBtn = document.getElementById("manualSubmitBtn");
  const manualInput = document.getElementById("manualPlateInput");
  const enterBtn = document.querySelector(".enterBtn");
  const exitBtn = document.querySelector(".exitBtn");
  const resetBtn = document.getElementById("resetBtn");

  if (manualSubmitBtn) {
    manualSubmitBtn.addEventListener("click", submitManualPlate);
  }

  if (manualInput) {
    manualInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        submitManualPlate();
      }
    });
  }

  if (enterBtn) {
    enterBtn.addEventListener("click", () => {
      triggerBackendAction("entry");
    });
  }

  if (exitBtn) {
    exitBtn.addEventListener("click", () => {
      triggerBackendAction("exit");
    });
  }

  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      resetAllUI();
    });
  }

  const historySearchInput = document.getElementById("historySearchInput");
  if (historySearchInput) {
    historySearchInput.addEventListener("input", (e) => {
      historySearchQuery = e.target.value.trim();
      renderHistoryTable(allHistoryItems);
    });
  }

  document.querySelectorAll(".statusFilterBtn").forEach((button) => {
    button.addEventListener("click", () => {
      historyStatusFilter = button.dataset.statusFilter || "all";

      document.querySelectorAll(".statusFilterBtn").forEach((item) => {
        item.classList.toggle("active", item === button);
      });

      renderHistoryTable(allHistoryItems);
    });
  });

  const viewAll = document.querySelector(".viewAll");
  if (viewAll) {
    viewAll.addEventListener("click", toggleAllHistory);
  }
});
function formatDbTime(value) {
  if (!value) return "--:--:--";

  // Nếu DB trả sẵn dạng "2026-06-05 09:13:08"
  const date = new Date(value.replace(" ", "T"));

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  const seconds = String(date.getSeconds()).padStart(2, "0");

  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const year = date.getFullYear();

  return `${hours}:${minutes}:${seconds} - ${day}/${month}/${year}`;
}

function getSessionStatusText(item) {
  if (item.status === "inside") {
    return "ĐÃ VÀO";
  }

  if (item.status === "exited") {
    return "ĐÃ RA";
  }

  return "KHÔNG RÕ";
}

function getStatusClass(item) {
  if (item.status === "inside") return "in";
  if (item.status === "exited") return "out";

  return "out";
}

function renderHistoryTable(items) {
  const tbody = document.getElementById("historyTableBody");

  if (!tbody) return;

  const filtered = filterHistoryBySearch(items);

  if (!filtered || filtered.length === 0) {
    const msg = historySearchQuery || historyStatusFilter !== "all"
      ? "Không tìm thấy kết quả"
      : "Chưa có dữ liệu ra vào";
    tbody.innerHTML = `
      <tr>
        <td colspan="5" class="emptyRow">${msg}</td>
      </tr>
    `;
    syncVehicleCount();
    return;
  }

  tbody.innerHTML = filtered
    .map((item, index) => {
      const stt = String(index + 1).padStart(2, "0");

      const plateText = item.plate_text || "--";

      const entryTime = item.entry_time
        ? formatDbTime(item.entry_time)
        : "--:--:--";

      const exitTime = item.exit_time
        ? formatDbTime(item.exit_time)
        : "--:--:--";

      const statusText = getSessionStatusText(item);
      const statusClass = getStatusClass(item);

      const exitCell =
        exitTime === "--:--:--"
          ? `<td class="empty">--:--:--</td>`
          : `<td>${exitTime}</td>`;

      return `
        <tr>
          <td>${stt}</td>
          <td>${entryTime}</td>
          <td><span class="plateMini">${plateText}</span></td>
          <td><span class="status ${statusClass}">${statusText}</span></td>
          ${exitCell}
        </tr>
      `;
    })
    .join("");
}

async function loadHistoryTable() {
  try {
    const url = showAllHistory
      ? `${API_BASE}/sessions/24h`
      : `${API_BASE}/sessions/latest`;

    const res = await fetch(url);
    const data = await res.json();

    if (!data.success) {
      console.log("Không lấy được lịch sử:", data.message);
      allHistoryItems = [];
      renderHistoryTable([]);
      return;
    }

    allHistoryItems = data.data || [];
    renderHistoryTable(allHistoryItems);
    syncVehicleCount();
  } catch (error) {
    console.log("Lỗi tải lịch sử:", error.message);
    allHistoryItems = [];
    renderHistoryTable([]);
    syncVehicleCount();
  }
}

function toggleAllHistory() {
  showAllHistory = !showAllHistory;

  const viewAll = document.querySelector(".viewAll");
  const timeBadge = document.querySelector(".timeBadge");

  if (showAllHistory) {
    if (viewAll) viewAll.textContent = "← QUAY LẠI";
    if (timeBadge) timeBadge.textContent = "TẤT CẢ 24H";
  } else {
    if (viewAll) viewAll.textContent = "XEM TẤT CẢ LỊCH SỬ →";
    if (timeBadge) timeBadge.textContent = "24 GIỜ QUA";
  }

  loadHistoryTable();
}

function filterHistoryBySearch(items) {
  const query = historySearchQuery.toUpperCase();

  return items.filter((item) => {
    const plate = (item.plate_text || "").toUpperCase();
    const matchSearch = !query || plate.includes(query);
    const matchStatus =
      historyStatusFilter === "all" || item.status === historyStatusFilter;

    return matchSearch && matchStatus;
  });
}
