let targets = JSON.parse(localStorage.getItem("lvcc_targets") || "[]");
let realtimeFetchTimer = null;
let allTableData = [];
let currentPage = 1;
const pageSize = 10; 

function saveTargets() { localStorage.setItem("lvcc_targets", JSON.stringify(targets)); }

async function checkPasscode() {
    const inputField = document.getElementById("passcodeInput");
    const passValue = inputField.value;
    const btn = document.querySelector("#loginScreen button");
    const errorMsg = document.getElementById("loginError");
    
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Verifying...';
    btn.disabled = true;
    errorMsg.style.display = "none";

    try {
        const res = await fetch("/api/admin/login", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ passcode: passValue })
        });
        
        if (res.ok) {
            document.getElementById("loginScreen").style.display = "none";
            document.getElementById("mainDashboard").style.display = "block";
            fetchStats();
        } else {
            errorMsg.style.display = "block";
            setTimeout(() => errorMsg.style.display = "none", 3000);
        }
    } catch (e) {
        errorMsg.textContent = "Server connection failed.";
        errorMsg.style.display = "block";
    } finally {
        btn.innerHTML = '<i class="fas fa-arrow-right-to-bracket"></i> Access Dashboard';
        btn.disabled = false;
        inputField.value = ""; 
    }
}

async function logout() {
    await fetch("/api/admin/logout", { method: "POST" });
    document.getElementById("mainDashboard").style.display = "none";
    document.getElementById("loginScreen").style.display = "flex";
}

function addTarget() {
    const name = document.getElementById("targetName").value.trim();
    const email = document.getElementById("targetEmail").value.trim();
    if (!name || !email) { alert("Fill in both fields."); return; }
    targets.push({ name, email });
    saveTargets();
    document.getElementById("targetName").value = "";
    document.getElementById("targetEmail").value = "";
    renderList();
}

function removeTarget(i) { targets.splice(i, 1); saveTargets(); renderList(); }

function renderList() {
    const list = document.getElementById("targetList");
    const btn = document.getElementById("sendBtn");
    if (!targets.length) {
        list.innerHTML = '<div class="empty-state"><i class="fas fa-users"></i>No targets added yet.</div>';
        btn.disabled = true; return;
    }
    list.innerHTML = targets.map((t, i) => `
        <div class="target-item">
        <div class="target-info">
            <div class="name">${t.name}</div>
            <div class="email">${t.email}</div>
        </div>
        <button class="remove-btn" onclick="removeTarget(${i})"><i class="fas fa-xmark"></i></button>
        </div>
    `).join("");
    btn.disabled = false;
}

async function fetchStats() {
    try {
        const res = await fetch("/api/stats");
        const data = await res.json();
        
        const totalSent = data.analytics.total_sent || 0;
        const totalCompromised = data.analytics.total_compromised || 0;
        
        document.getElementById("statSent").textContent = totalSent;
        document.getElementById("statClicked").textContent = data.analytics.total_clicked || 0;
        document.getElementById("statRate").textContent = data.analytics.click_rate || "0%";
        document.getElementById("statAttempted").textContent = totalCompromised;
        
        const attemptedRate = totalSent > 0 ? ((totalCompromised / totalSent) * 100).toFixed(1) + "%" : "0%";
        document.getElementById("statAttemptedRate").textContent = attemptedRate;

        allTableData = data.table || [];
        updateTableUI();
        
    } catch (e) { console.error(e); }
}

function updateTableUI() {
    const searchInput = document.getElementById("tableSearch").value.toLowerCase();
    const filterVal = document.getElementById("statusFilter").value;

    let filteredData = allTableData.filter(t => {
        const matchesSearch = t.email.toLowerCase().includes(searchInput);
        let matchesFilter = true;
        
        if (filterVal === "clicked") matchesFilter = t.clicked;
        else if (filterVal === "attempted") matchesFilter = t.compromised;
        else if (filterVal === "both") matchesFilter = t.clicked && t.compromised;

        return matchesSearch && matchesFilter;
    });

    const totalPages = Math.ceil(filteredData.length / pageSize) || 1;
    if (currentPage > totalPages) currentPage = totalPages; 
    
    const startIndex = (currentPage - 1) * pageSize;
    const pagedData = filteredData.slice(startIndex, startIndex + pageSize);

    const tbody = document.getElementById("tableBody");
    if (!pagedData.length) {
        tbody.innerHTML = '<tr class="empty-row"><td colspan="4"><i class="fas fa-inbox" style="display:block;font-size:22px;margin-bottom:8px;opacity:.2;"></i>No matching records found.</td></tr>';
    } else {
        tbody.innerHTML = pagedData.map(t => `
         <tr>
            <td>${t.email}</td>
            <td><span class="tag ${t.sent ? 'tag-yes' : 'tag-no'}">${t.sent ? '✓ Sent' : '–'}</span></td>
            <td><span class="tag ${t.clicked ? 'tag-click' : 'tag-no'}">${t.clicked ? '✓ Clicked' : '–'}</span></td>
            <td><span class="tag ${t.compromised ? 'tag-attempted' : 'tag-no'}">${t.compromised ? '⚠ Yes' : '–'}</span></td>
        </tr>
        `).join("");
    }

    document.getElementById("pageInfo").textContent = `Page ${currentPage} of ${totalPages} (${filteredData.length} records)`;
    document.getElementById("btnPrev").disabled = currentPage === 1;
    document.getElementById("btnNext").disabled = currentPage === totalPages || totalPages === 0;
}

function changePage(direction) {
    currentPage += direction;
    updateTableUI();
}

function scheduleStatsRefresh() {
    if(realtimeFetchTimer) clearTimeout(realtimeFetchTimer);
    realtimeFetchTimer = setTimeout(() => fetchStats(), 200);
}

function handleRealtimeMessage(msg) {
    if(!msg || !msg.type) return;
    if(["sent","opened","clicked","compromised","stats_update"].includes(msg.type)){
        scheduleStatsRefresh();
    }
}

function updateLivePillStatus(online) {
    const pill = document.querySelector(".live-pill");
    const dot = document.querySelector(".live-dot");
    if(!pill || !dot) return;
    dot.style.background = online ? "#22c55e" : "#ef4444";
    pill.title = online ? "Real-time connected" : "Reconnecting...";
}

function setupRealtime() {
    window.addEventListener("lvcc:ws-message", (event) => handleRealtimeMessage(event.detail));
    window.addEventListener("lvcc:ws-status", (event) => updateLivePillStatus(Boolean(event.detail?.online)));
}

async function sendCampaign() {
    if(!targets.length) return;
    const btn = document.getElementById("sendBtn");
    
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending…';
    btn.disabled = true;
    
    try {
        const res = await fetch("/api/send-email", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                targets: targets,
                version: "v2" 
            })
        });
        const result = await res.json();
        
        if(res.ok && result.message.includes("Sent to")) {
            showFeedback("Email sent successfully!","var(--success)");
            targets = [];
            saveTargets();
            fetchStats();
        } else {
            showFeedback(result.message, "var(--danger)");
        }
    } catch {
        showFeedback("Connection failed.", "var(--danger)");
    } finally {
        btn.innerHTML = '<i class="fas fa-paper-plane"></i> Send Simulation (V2)';
        renderList(); 
    }
}

function showFeedback(msg, color) {
    const el = document.getElementById("sendFeedback");
    el.style.color = color; el.textContent = msg; el.style.display = "block";
    setTimeout(() => el.style.display = "none", 5000);
}

(async function init() {
    setupRealtime();
    renderList();
    
    try {
        const res = await fetch("/api/admin/check-session");
        if (res.ok) {
            document.getElementById("loginScreen").style.display="none";
            document.getElementById("mainDashboard").style.display="block";
            fetchStats();
        }
    } catch (e) {
        console.warn("Session check failed:", e);
    }
})();