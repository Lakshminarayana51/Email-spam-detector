import os
import time
import json
import csv
import io
import uuid
import imaplib
import email
from email.header import decode_header
from typing import Dict, Any, List
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, Response, session

from utils.predictor import predictor
from utils.email_reader import IMAPEmailMonitor

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'sentrymail_super_secret_session_key_2026')

# SERVER-SIDE SESSION MEMORY STORE
# Key: session_id (UUID string), Value: { "emails": [...], "stats": {...}, "user": "..." }
SESSION_STORE: Dict[str, Dict[str, Any]] = {}

# Active IMAP background monitors per session
ACTIVE_MONITORS: Dict[str, IMAPEmailMonitor] = {}

def get_or_create_sid() -> str:
    """Ensures each browser gets a unique session ID cookie."""
    if 'sid' not in session:
        session['sid'] = str(uuid.uuid4())
        session.permanent = True
    sid = session['sid']
    if sid not in SESSION_STORE:
        SESSION_STORE[sid] = {
            "emails": [],
            "stats": {"total_analyzed": 0, "total_spam": 0, "total_ham": 0},
            "user": ""
        }
    return sid

def save_session_email(sid: str, scored_email: Dict[str, Any]):
    """Saves a scored email into the server-side memory store for the active session."""
    store = SESSION_STORE.get(sid)
    if not store:
        return

    emails = store["emails"]
    stats = store["stats"]

    # Avoid duplicate IDs
    for item in emails:
        if item.get('id') == scored_email.get('id'):
            return

    emails.insert(0, scored_email)
    # Cap session list to latest 200 items
    store["emails"] = emails[:200]

    stats["total_analyzed"] += 1
    if scored_email.get("is_spam"):
        stats["total_spam"] += 1
    else:
        stats["total_ham"] += 1

def scan_inbox_synchronously(sid: str, host: str, port: int, user: str, password: str, limit: int = 30) -> List[Dict[str, Any]]:
    """
    Scans real IMAP mailbox synchronously and populates server-side session memory.
    """
    clean_pass = password.replace(" ", "").strip()
    imap_conn = imaplib.IMAP4_SSL(host, port)
    imap_conn.login(user, clean_pass)
    
    status, _ = imap_conn.select("INBOX", readonly=True)
    if status != 'OK':
        imap_conn.logout()
        raise Exception("Failed to access INBOX")

    status, messages = imap_conn.search(None, 'ALL')
    if status != 'OK' or not messages[0]:
        imap_conn.logout()
        return []

    uids = messages[0].split()
    recent_uids = uids[-limit:]
    
    scored_list = []
    for uid in reversed(recent_uids):
        uid_str = uid.decode('utf-8') if isinstance(uid, bytes) else str(uid)
        unique_id = f"mail_{user}_{uid_str}"

        res, data = imap_conn.fetch(uid, '(RFC822)')
        if res != 'OK' or not data or not data[0]:
            continue

        raw_email = data[0][1]
        if not isinstance(raw_email, bytes):
            continue

        msg = email.message_from_bytes(raw_email)

        # Decode subject
        subject_raw = msg.get('Subject', '(No Subject)')
        decoded_subj = []
        try:
            for content, encoding in decode_header(subject_raw):
                if isinstance(content, bytes):
                    decoded_subj.append(content.decode(encoding or 'utf-8', errors='replace'))
                else:
                    decoded_subj.append(str(content))
            subject = "".join(decoded_subj)
        except Exception:
            subject = str(subject_raw)

        sender = str(msg.get('From', 'Unknown Sender'))

        body_text = ""
        html_text = ""
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    if "attachment" in str(part.get("Content-Disposition", "")):
                        continue
                    c_type = part.get_content_type()
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        txt = payload.decode(charset, errors='replace')
                        if c_type == "text/plain":
                            body_text += txt + "\n"
                        elif c_type == "text/html":
                            html_text += txt + "\n"
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or 'utf-8'
                    body_text = payload.decode(charset, errors='replace')
        except Exception:
            pass

        body = body_text.strip() if body_text.strip() else html_text.strip()
        if not body and msg.get_payload():
            body = str(msg.get_payload())

        pred = predictor.predict(subject, body)

        scored = {
            "id": unique_id,
            "subject": subject or "(No Subject)",
            "sender": sender,
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "body": body[:300] + ("..." if len(body) > 300 else ""),
            "source": "LIVE INBOX",
            "label": pred["label"],
            "is_spam": pred["is_spam"],
            "confidence": pred["confidence"],
            "spam_score": pred["spam_score"],
            "triggers": pred.get("triggers", []),
            "timestamp": time.strftime("%H:%M:%S")
        }

        scored_list.append(scored)
        save_session_email(sid, scored)

    try:
        imap_conn.logout()
    except Exception:
        pass

    return scored_list

# --- SERVER-RENDERED ROUTES ---

@app.route('/')
def dashboard():
    """Main dashboard view."""
    get_or_create_sid()
    return render_template('index.html')

@app.route('/test')
def test_page():
    """Manual email testing page."""
    get_or_create_sid()
    return render_template('test_email.html')

# --- REST API ENDPOINTS ---

@app.route('/api/status', methods=['GET'])
def get_status():
    """Returns model status and session status."""
    sid = get_or_create_sid()
    store = SESSION_STORE[sid]
    user = store["user"]
    total = store["stats"]["total_analyzed"]
    
    is_active = bool(user or total > 0)
    
    return jsonify({
        "model_ready": predictor.is_ready(),
        "live_monitoring_enabled": is_active,
        "imap_host": "imap.gmail.com" if user else "Not Configured",
        "imap_user": user if user else ("Active Session" if is_active else "Not Configured"),
        "imap_status": f"Connected ({user})" if user else ("Active Session" if is_active else "Disconnected"),
        "imap_error": None
    })

@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    """Returns trained model performance metrics."""
    metrics_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'model', 'metrics.json'
    )
    if os.path.exists(metrics_path):
        with open(metrics_path, 'r') as f:
            data = json.load(f)
        return jsonify({"success": True, "metrics": data})
    return jsonify({"success": False, "error": "Metrics file not found"}), 404

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Returns session-isolated aggregated detection statistics."""
    sid = get_or_create_sid()
    stats = SESSION_STORE[sid]["stats"]
    total = stats["total_analyzed"]
    spam = stats["total_spam"]
    ham = stats["total_ham"]
    spam_pct = round((spam / total * 100.0), 1) if total > 0 else 0.0

    return jsonify({
        "total_analyzed": total,
        "total_spam": spam,
        "total_ham": ham,
        "spam_percentage": spam_pct
    })

@app.route('/api/emails', methods=['GET'])
def get_emails():
    """Returns session-isolated classified email logs."""
    sid = get_or_create_sid()
    filter_type = request.args.get('filter', 'all').lower()
    limit = int(request.args.get('limit', 50))

    emails = SESSION_STORE[sid]["emails"]
    
    if filter_type == 'spam':
        emails = [e for e in emails if e.get('is_spam')]
    elif filter_type == 'ham':
        emails = [e for e in emails if not e.get('is_spam')]

    return jsonify({
        "count": len(emails[:limit]),
        "emails": emails[:limit]
    })

@app.route('/api/test', methods=['POST'])
def test_email():
    """Runs inference on manually submitted subject + body."""
    sid = get_or_create_sid()
    data = request.json or {}
    subject = data.get('subject', '').strip()
    body = data.get('body', '').strip()

    if not subject and not body:
        return jsonify({"error": "Subject or body must be provided."}), 400

    prediction = predictor.predict(subject, body)

    scored_email = {
        "id": f"manual_{int(time.time() * 1000)}",
        "subject": subject or "(No Subject)",
        "sender": "Manual Tester",
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "body": body,
        "source": "MANUAL",
        "label": prediction["label"],
        "is_spam": prediction["is_spam"],
        "confidence": prediction["confidence"],
        "spam_score": prediction["spam_score"],
        "triggers": prediction.get("triggers", []),
        "timestamp": time.strftime("%H:%M:%S")
    }

    save_session_email(sid, scored_email)

    return jsonify({
        "success": True,
        "prediction": prediction,
        "email": scored_email
    })

@app.route('/api/seed_demo', methods=['POST'])
def seed_demo():
    """Seeds realistic demo emails into the active browser session memory."""
    sid = get_or_create_sid()
    demo_samples = [
        {
            "subject": "URGENT: Verify your bank account access now",
            "sender": "alert@security-bank-update.com",
            "body": "Dear customer, suspicious activity was detected on your account. Please log in immediately at http://verify-bank-id.net to restore access."
        },
        {
            "subject": "Sprint Review & Demo Agenda for Thursday",
            "sender": "jason.engineering@company.com",
            "body": "Hi team, please prepare your slides for the Sprint Review call this Thursday. We will highlight the API performance improvements."
        },
        {
            "subject": "CLAIM YOUR FREE $1,000 AMAZON GIFT CARD!",
            "sender": "rewards@free-gifts-online.biz",
            "body": "You have been selected to win a $1,000 Amazon gift card! Click here to complete a quick 1-minute survey and claim your code."
        },
        {
            "subject": "Flight Booking Confirmation #LH-9021",
            "sender": "reservations@lufthansa.com",
            "body": "Your flight from Frankfurt to New York on August 12 is confirmed. Download your mobile boarding pass from the Lufthansa app."
        },
        {
            "subject": "Double your Crypto portfolio in 48 hours!!",
            "sender": "invest@bitcoin-double-fast.org",
            "body": "Guaranteed 200% return on Ethereum and Bitcoin deposits! Limited time promo. Deposit funds now at http://double-crypto-pool.xyz"
        },
        {
            "subject": "Design Systems Guidelines Sync",
            "sender": "maria.design@company.com",
            "body": "Hey everyone, I updated the typography scale and color variables in Figma. Please review the updated design token documentation."
        }
    ]

    count_added = 0
    for sample in demo_samples:
        pred = predictor.predict(sample['subject'], sample['body'])
        scored = {
            "id": f"demo_{int(time.time() * 1000)}_{count_added}",
            "subject": sample['subject'],
            "sender": sample['sender'],
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "body": sample['body'],
            "source": "DEMO",
            "label": pred["label"],
            "is_spam": pred["is_spam"],
            "confidence": pred["confidence"],
            "spam_score": pred["spam_score"],
            "triggers": pred.get("triggers", []),
            "timestamp": time.strftime("%H:%M:%S")
        }
        save_session_email(sid, scored)
        count_added += 1

    stats = SESSION_STORE[sid]["stats"]
    return jsonify({
        "success": True,
        "message": f"Seeded {count_added} demo emails into session.",
        "stats": stats
    })

@app.route('/api/config/imap', methods=['POST'])
def update_imap_config():
    """Connects user mailbox, saves to server-side session memory, and scans inbox."""
    sid = get_or_create_sid()
    data = request.json or {}
    host = data.get('host', 'imap.gmail.com').strip()
    port = int(data.get('port', 993))
    user = data.get('user', '').strip()
    password = data.get('password', '').replace(" ", "").strip()
    mailbox = data.get('mailbox', 'INBOX').strip()

    if not user or not password:
        return jsonify({"error": "Email user and App Password are required."}), 400

    try:
        scored_items = scan_inbox_synchronously(sid, host, port, user, password, limit=30)
        SESSION_STORE[sid]["user"] = user

        # Start persistent background monitor for local server if active
        if sid in ACTIVE_MONITORS:
            ACTIVE_MONITORS[sid].stop()
        
        cb = lambda scored: save_session_email(sid, scored)
        monitor = IMAPEmailMonitor(callback=cb)
        monitor.configure(host, port, user, password, mailbox)
        try:
            monitor.start()
            ACTIVE_MONITORS[sid] = monitor
        except Exception:
            pass

        return jsonify({
            "success": True,
            "message": f"Successfully connected to {user}! Scanned {len(scored_items)} emails from inbox.",
            "count": len(scored_items)
        })
    except Exception as e:
        err_msg = str(e)
        if "AUTHENTICATIONFAILED" in err_msg or "Invalid credentials" in err_msg:
            return jsonify({
                "error": "Authentication Failed: Please check 1) Your email address, 2) 16-character App Password, 3) Enable IMAP in Gmail Settings."
            }), 401
        return jsonify({"error": f"IMAP Connection Error: {err_msg}"}), 400

@app.route('/api/disconnect', methods=['POST'])
def disconnect_session():
    """Clears user session memory & stops active background scanner."""
    sid = get_or_create_sid()
    if sid in ACTIVE_MONITORS:
        try:
            ACTIVE_MONITORS[sid].stop()
            del ACTIVE_MONITORS[sid]
        except Exception:
            pass

    if sid in SESSION_STORE:
        SESSION_STORE[sid] = {
            "emails": [],
            "stats": {"total_analyzed": 0, "total_spam": 0, "total_ham": 0},
            "user": ""
        }

    session.clear()
    return jsonify({
        "success": True,
        "message": "Session disconnected and mailbox details cleared successfully."
    })

@app.route('/api/export', methods=['GET'])
def export_csv():
    """Export currently stored session emails as downloadable CSV."""
    sid = get_or_create_sid()
    emails = SESSION_STORE[sid]["emails"]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Timestamp', 'Subject', 'Sender', 'Source', 'Label', 'Is_Spam', 'Confidence', 'Spam_Score', 'Triggers', 'Body'])

    for email_item in emails:
        writer.writerow([
            email_item.get('id', ''),
            email_item.get('date', ''),
            email_item.get('subject', ''),
            email_item.get('sender', ''),
            email_item.get('source', ''),
            email_item.get('label', ''),
            email_item.get('is_spam', False),
            email_item.get('confidence', 0),
            email_item.get('spam_score', 0),
            ", ".join(email_item.get('triggers', [])),
            email_item.get('body', '')
        ])

    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=sentrymail_export.csv"
    return response

if __name__ == '__main__':
    print("=" * 60)
    print("SentryMail Server-Side Session Memory Web Application Launching")
    print("Dashboard available at: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=False)
