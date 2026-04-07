const PASSCODE="admin123";
let targets=JSON.parse(localStorage.getItem("lvcc_targets")||"[]");
let realtimeFetchTimer=null;

function saveTargets(){localStorage.setItem("lvcc_targets",JSON.stringify(targets));}

function checkPasscode(){
    if(document.getElementById("passcodeInput").value===PASSCODE){
        localStorage.setItem("lvcc_session","1");
        document.getElementById("loginScreen").style.display="none";
        document.getElementById("mainDashboard").style.display="block";
        fetchStats();
    } else {
        const e=document.getElementById("loginError");
        e.style.display="block";
        setTimeout(()=>e.style.display="none",3000);
    }
}

function logout(){
    localStorage.removeItem("lvcc_session");
    document.getElementById("passcodeInput").value="";
    document.getElementById("mainDashboard").style.display="none";
    document.getElementById("loginScreen").style.display="flex";
}

function addTarget(){
    const name=document.getElementById("targetName").value.trim();
    const email=document.getElementById("targetEmail").value.trim();
    if(!name||!email){alert("Fill in both fields.");return;}
    targets.push({name,email});
    saveTargets();
    document.getElementById("targetName").value="";
    document.getElementById("targetEmail").value="";
    renderList();
}

function removeTarget(i){targets.splice(i,1);saveTargets();renderList();}

function renderList(){
    const list=document.getElementById("targetList");
    const btn=document.getElementById("sendBtn");
    if(!targets.length){
        list.innerHTML='<div class="empty-state"><i class="fas fa-users"></i>No targets added yet.</div>';
        btn.disabled=true;return;
    }
    list.innerHTML=targets.map((t,i)=>`
        <div class="target-item">
        <div class="target-info">
            <div class="name">${t.name}</div>
            <div class="email">${t.email}</div>
        </div>
        <button class="remove-btn" onclick="removeTarget(${i})"><i class="fas fa-xmark"></i></button>
        </div>
    `).join("");
    btn.disabled=false;
}

async function fetchStats(){
    try{
        const res=await fetch("/api/stats");
        const data=await res.json();
        document.getElementById("statSent").textContent=data.analytics.total_sent;
        document.getElementById("statClicked").textContent=data.analytics.total_clicked;
        document.getElementById("statRate").textContent=data.analytics.click_rate;
        if(document.getElementById("statCompromised"))document.getElementById("statCompromised").textContent=data.analytics.total_compromised ?? "—";
        
        const tbody=document.getElementById("tableBody");
        if(!data.table.length){
            tbody.innerHTML='<tr class="empty-row"><td colspan="4"><i class="fas fa-inbox" style="display:block;font-size:22px;margin-bottom:8px;opacity:.2;"></i>No data yet.</td></tr>';
            return;
        }
        tbody.innerHTML=data.table.map(t=>`
         <tr>
            <td>${t.email}</td>
            <td><span class="tag ${t.sent?'tag-yes':'tag-no'}">${t.sent?'✓ Sent':'–'}</span></td>
            <!-- <td><span class="tag ${t.opened?'tag-yes':'tag-no'}">${t.opened?'✓ Opened':'–'}</span></td> -->
            <td><span class="tag ${t.clicked?'tag-click':'tag-no'}">${t.clicked?'✓ Clicked':'–'}</span></td>
            <td><span class="tag ${t.compromised?'tag-compromised':'tag-no'}">${t.compromised?'⚠ Yes':'–'}</span></td>
        </tr>
        `).join("");

        filterTable(); 
        
    }catch(e){console.error(e);}
}

function scheduleStatsRefresh(){
    if(realtimeFetchTimer) clearTimeout(realtimeFetchTimer);
    realtimeFetchTimer=setTimeout(()=>fetchStats(),200);
}

function handleRealtimeMessage(msg){
    if(!msg||!msg.type) return;
    if(["sent","opened","clicked","compromised","stats_update"].includes(msg.type)){
        scheduleStatsRefresh();
    }
}

function updateLivePillStatus(online){
    const pill=document.querySelector(".live-pill");
    const dot=document.querySelector(".live-dot");
    if(!pill||!dot) return;
    dot.style.background=online?"#22c55e":"#ef4444";
    pill.title=online?"Real-time connected":"Reconnecting...";
}

function setupRealtime(){
    window.addEventListener("lvcc:ws-message",(event)=>handleRealtimeMessage(event.detail));
    window.addEventListener("lvcc:ws-status",(event)=>updateLivePillStatus(Boolean(event.detail?.online)));
}

async function sendCampaign(){
    if(!targets.length) return;
    const btn = document.getElementById("sendBtn");
    const selectedVersion = (document.querySelector('input[name="versionSelect"]:checked')||{value:"v1"}).value;
    
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending…';
    btn.disabled = true;
    
    try {
        const res = await fetch("/api/send-email", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                targets: targets,
                version: selectedVersion
            })
        });
        const result = await res.json();
        
        if(res.ok && result.message.includes("Sent to")){
            showFeedback("Campaign sent!","var(--success)");
            targets = [];
            saveTargets();
            fetchStats();
        } else {
            showFeedback(result.message,"var(--danger)");
        }
    } catch {
        showFeedback("Connection failed.","var(--danger)");
    } finally {
        btn.innerHTML = '<i class="fas fa-paper-plane"></i> Send Simulation';
        renderList(); 
    }
}


function filterTable() {
    const input = document.getElementById("tableSearch").value.toLowerCase();
    const rows = document.querySelectorAll("#tableBody tr:not(.empty-row)");
    
    rows.forEach(row => {
        const emailCell = row.querySelector("td:first-child"); 
        if (emailCell) {
            const emailText = emailCell.textContent.toLowerCase();
            row.style.display = emailText.includes(input) ? "" : "none";
        }
    });
}

function showFeedback(msg,color){
    const el=document.getElementById("sendFeedback");
    el.style.color=color;el.textContent=msg;el.style.display="block";
    setTimeout(()=>el.style.display="none",5000);
}

(function init(){
    setupRealtime();
    if(localStorage.getItem("lvcc_session")==="1"){
        document.getElementById("loginScreen").style.display="none";
        document.getElementById("mainDashboard").style.display="block";
        renderList();
        fetchStats();
    } else {
        renderList();
    }
})();