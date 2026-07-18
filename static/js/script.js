/* SentryMail — Interactive Frontend Script */

let currentFilter = 'all';
let pollTimer = null;
let cachedEmails = [];

document.addEventListener('DOMContentLoaded', () => {
    // Initial fetch
    fetchSystemStatus();
    fetchStats();
    fetchEmailFeed();

    // Setup polling every 3 seconds
    pollTimer = setInterval(() => {
        fetchSystemStatus();
        fetchStats();
        fetchEmailFeed();
    }, 3000);
});

// Select provider preset in connection modal
function selectProvider(provider) {
    const hostInput = document.getElementById('imapHost');
    const portInput = document.getElementById('imapPort');
    const passHelp = document.getElementById('passHelpText');

    document.querySelectorAll('.preset-buttons button').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');

    if (provider === 'gmail') {
        hostInput.value = 'imap.gmail.com';
        portInput.value = '993';
        passHelp.innerHTML = '<strong>For Gmail:</strong> Generate a 16-character <em>App Password</em> (requires 2-Step Verification) at: <a href="https://myaccount.google.com/apppasswords" target="_blank">Google Security -> App Passwords</a>.';
    } else if (provider === 'outlook') {
        hostInput.value = 'outlook.office365.com';
        portInput.value = '993';
        passHelp.innerHTML = '<strong>For Outlook/Hotmail:</strong> Use your regular password or generate an App Password at <a href="https://account.live.com/proofs/manage/additional" target="_blank">Microsoft Account Security</a>.';
    } else if (provider === 'yahoo') {
        hostInput.value = 'imap.mail.yahoo.com';
        portInput.value = '993';
        passHelp.innerHTML = '<strong>For Yahoo Mail:</strong> Generate an App Password at <a href="https://login.yahoo.com/account/security" target="_blank">Yahoo Account Security</a>.';
    } else {
        hostInput.value = '';
        portInput.value = '993';
        passHelp.innerHTML = 'Enter your custom email provider\'s IMAP host and credentials.';
    }
}

// Fetch system & model status
async function fetchSystemStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();

        const modelDot = document.getElementById('modelStatusDot');
        const modelText = document.getElementById('modelStatusText');
        if (modelDot && modelText) {
            if (data.model_ready) {
                modelDot.className = 'status-indicator ready';
                modelText.textContent = 'ANN Engine Ready (.keras)';
            } else {
                modelDot.className = 'status-indicator error';
                modelText.textContent = 'Model Not Loaded (Run train_model.py)';
            }
        }

        const imapDot = document.getElementById('imapStatusDot');
        const imapText = document.getElementById('imapStatusText');
        const imapUserText = document.getElementById('imapUserText');
        const imapBtnText = document.getElementById('imapBtnText');

        if (imapDot && imapText) {
            if (data.live_monitoring_enabled) {
                imapDot.className = 'status-indicator active';
                imapText.textContent = data.imap_status || 'Active Scanning';
            } else {
                imapDot.className = 'status-indicator';
                imapText.textContent = data.imap_status || 'Disconnected';
            }
        }

        if (imapUserText) {
            imapUserText.textContent = data.imap_user || 'None configured';
        }

        if (imapBtnText) {
            imapBtnText.textContent = data.live_monitoring_enabled ? 'Connected' : 'Connect Real Inbox';
        }

    } catch (err) {
        console.error('Error fetching status:', err);
    }
}

// Fetch live detection statistics
async function fetchStats() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();

        const totalEl = document.getElementById('statTotal');
        const spamEl = document.getElementById('statSpam');
        const hamEl = document.getElementById('statHam');
        const spamSubEl = document.getElementById('statSpamSub');
        const spamPercentEl = document.getElementById('statSpamPercent');
        const threatBar = document.getElementById('threatMeterBar');

        if (totalEl) totalEl.textContent = data.total_analyzed.toLocaleString();
        if (spamEl) spamEl.textContent = data.total_spam.toLocaleString();
        if (hamEl) hamEl.textContent = data.total_ham.toLocaleString();

        if (spamSubEl) spamSubEl.textContent = `${data.spam_percentage}% of total volume`;
        if (spamPercentEl) spamPercentEl.textContent = `${data.spam_percentage}% Threat Level`;
        if (threatBar) threatBar.style.width = `${Math.min(data.spam_percentage, 100)}%`;

    } catch (err) {
        console.error('Error fetching stats:', err);
    }
}

// Fetch scored email feed table
async function fetchEmailFeed() {
    const tbody = document.getElementById('emailTableBody');
    if (!tbody) return;

    try {
        const res = await fetch(`/api/emails?filter=${currentFilter}&limit=50`);
        const data = await res.json();

        cachedEmails = data.emails || [];

        if (!data.emails || data.emails.length === 0) {
            tbody.innerHTML = `
                <tr class="empty-row">
                    <td colspan="7">
                        <div class="empty-state">
                            <i class="fa-solid fa-envelope-open-text"></i>
                            <p>No emails found for filter "${currentFilter}".</p>
                            <span class="sub-state">Click <strong>"Connect Real Inbox"</strong> or <strong>"Seed Demo Data"</strong> to scan emails for spam.</span>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        let html = '';
        data.emails.forEach((email, idx) => {
            const isSpam = email.is_spam;
            const badgeClass = isSpam ? 'badge spam' : 'badge ham';
            const badgeIcon = isSpam ? 'fa-solid fa-shield-cat' : 'fa-solid fa-circle-check';
            const sourceClass = email.source.includes('LIVE') ? 'source-tag live' : 'source-tag manual';

            let triggersHtml = '';
            if (email.triggers && email.triggers.length > 0) {
                triggersHtml = email.triggers.map(t => `<span class="btn-xs" style="background: rgba(239,68,68,0.15); color: #f87171; border: 1px solid rgba(239,68,68,0.3); font-size: 0.7rem;">${escapeHtml(t)}</span>`).join(' ');
            } else {
                triggersHtml = `<span class="text-dim" style="font-size: 0.75rem;">None</span>`;
            }

            html += `
                <tr style="cursor: pointer;" onclick="openEmailInspector(${idx})" title="Click to inspect neural analysis">
                    <td>
                        <span class="${badgeClass}">
                            <i class="${badgeIcon}"></i> ${email.label}
                        </span>
                    </td>
                    <td>
                        <strong>${escapeHtml(email.subject)}</strong>
                        <br>
                        <small class="text-dim">${escapeHtml(email.body)}</small>
                    </td>
                    <td><span class="mono">${escapeHtml(email.sender)}</span></td>
                    <td><span class="${sourceClass}">${email.source}</span></td>
                    <td>${triggersHtml}</td>
                    <td>
                        <strong>${email.confidence}%</strong>
                        <br>
                        <small class="text-dim">Score: ${email.spam_score}</small>
                    </td>
                    <td><span class="text-dim font-mono">${email.timestamp}</span></td>
                </tr>
            `;
        });

        tbody.innerHTML = html;

    } catch (err) {
        console.error('Error fetching email feed:', err);
    }
}

// Open email inspector modal
function openEmailInspector(index) {
    const email = cachedEmails[index];
    if (!email) return;

    const modal = document.getElementById('emailDetailModal');
    const badge = document.getElementById('inspectBadge');
    const subject = document.getElementById('inspectSubject');
    const sender = document.getElementById('inspectSender');
    const label = document.getElementById('inspectLabel');
    const conf = document.getElementById('inspectConfidence');
    const score = document.getElementById('inspectScore');
    const triggersList = document.getElementById('inspectTriggersList');
    const body = document.getElementById('inspectBodyText');

    if (email.is_spam) {
        badge.className = 'badge-large spam';
        badge.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> SPAM THREAT';
        label.textContent = 'SPAM';
        label.style.color = '#f87171';
    } else {
        badge.className = 'badge-large ham';
        badge.innerHTML = '<i class="fa-solid fa-circle-check"></i> LEGITIMATE (HAM)';
        label.textContent = 'HAM';
        label.style.color = '#34d399';
    }

    subject.textContent = email.subject || '(No Subject)';
    sender.textContent = `From: ${email.sender} (${email.source})`;
    conf.textContent = `${email.confidence}%`;
    score.textContent = email.spam_score.toFixed(4);
    body.textContent = email.body;

    if (email.triggers && email.triggers.length > 0) {
        triggersList.innerHTML = email.triggers.map(t => `<span class="badge spam" style="font-size: 0.75rem;">${escapeHtml(t)}</span>`).join('');
    } else {
        triggersList.innerHTML = '<span class="text-dim" style="font-size: 0.8rem;">No high-risk keyword triggers detected.</span>';
    }

    if (modal) modal.classList.remove('hidden');
}

function closeEmailModal() {
    const modal = document.getElementById('emailDetailModal');
    if (modal) modal.classList.add('hidden');
}

// Filter button toggle
function setFilter(filterType) {
    currentFilter = filterType;
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.filter === filterType);
    });
    fetchEmailFeed();
}

// Seed Demo Data
async function seedDemoData() {
    const btn = document.getElementById('btnSeedDemo');
    if (btn) btn.disabled = true;

    try {
        const res = await fetch('/api/seed_demo', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            fetchStats();
            fetchEmailFeed();
        }
    } catch (err) {
        console.error('Error seeding demo data:', err);
    } finally {
        if (btn) btn.disabled = false;
    }
}

// IMAP Modal Handling
function openIMAPModal() {
    const modal = document.getElementById('imapModal');
    if (modal) modal.classList.remove('hidden');
}

function closeIMAPModal() {
    const modal = document.getElementById('imapModal');
    if (modal) modal.classList.add('hidden');
}

async function submitIMAPConfig(event) {
    event.preventDefault();
    const host = document.getElementById('imapHost').value;
    const port = document.getElementById('imapPort').value;
    const user = document.getElementById('emailUser').value;
    const password = document.getElementById('emailPassword').value;

    const msgDiv = document.getElementById('imapModalMsg');
    const saveBtn = document.getElementById('btnSaveIMAP');

    saveBtn.disabled = true;
    saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Connecting & Scanning...';

    try {
        const res = await fetch('/api/config/imap', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ host, port, user, password })
        });

        const data = await res.json();

        if (res.ok && data.success) {
            msgDiv.className = 'modal-message success';
            msgDiv.textContent = data.message + ' — Scanning inbox...';
            msgDiv.classList.remove('hidden');
            setTimeout(() => {
                closeIMAPModal();
                fetchSystemStatus();
                fetchStats();
                fetchEmailFeed();
            }, 2000);
        } else {
            msgDiv.className = 'modal-message error';
            msgDiv.textContent = data.error || 'Failed to connect to IMAP server. Verify App Password.';
            msgDiv.classList.remove('hidden');
        }
    } catch (err) {
        msgDiv.className = 'modal-message error';
        msgDiv.textContent = 'Network error configuring IMAP.';
        msgDiv.classList.remove('hidden');
    } finally {
        saveBtn.disabled = false;
        saveBtn.innerHTML = '<i class="fa-solid fa-satellite-dish"></i> Connect & Scan Inbox';
    }
}

// Manual Test Inference Handler
async function runTestInference(event) {
    event.preventDefault();
    const subject = document.getElementById('testSubject').value;
    const body = document.getElementById('testBody').value;
    const btn = document.getElementById('btnRunInference');

    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Analyzing...';

    try {
        const res = await fetch('/api/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ subject, body })
        });

        const data = await res.json();

        if (res.ok && data.success) {
            const pred = data.prediction;
            
            document.getElementById('resultPlaceholder').classList.add('hidden');
            document.getElementById('resultContent').classList.remove('hidden');

            const badge = document.getElementById('resultBadge');
            const icon = document.getElementById('resultIcon');
            const labelText = document.getElementById('resultLabelText');

            if (pred.is_spam) {
                badge.className = 'badge-large spam';
                icon.className = 'fa-solid fa-triangle-exclamation';
                labelText.textContent = 'SPAM THREAT';
            } else {
                badge.className = 'badge-large ham';
                icon.className = 'fa-solid fa-circle-check';
                labelText.textContent = 'LEGITIMATE (HAM)';
            }

            document.getElementById('resultConfidence').textContent = `${pred.confidence}%`;
            document.getElementById('rawScoreText').textContent = pred.spam_score.toFixed(4);
            document.getElementById('probBarFill').style.width = `${(pred.spam_score * 100).toFixed(1)}%`;
            document.getElementById('snippetText').textContent = pred.cleaned_text || '(No tokens)';

        } else {
            alert(data.error || 'Classification failed.');
        }

    } catch (err) {
        console.error('Error running test inference:', err);
        alert('Failed to connect to backend.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Classify Email Now';
    }
}

function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
