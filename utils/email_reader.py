import os
import time
import imaplib
import email
from email.header import decode_header
import threading
import traceback
from typing import Callable, Optional, Dict, Any, List
from dotenv import load_dotenv

from utils.predictor import predictor

load_dotenv()

class IMAPEmailMonitor:
    """
    Background daemon that monitors an IMAP mailbox in read-only mode,
    fetches inbox emails (including recent and unseen messages), classifies them using
    SpamPredictor, and emits results to a subscriber callback.
    """
    def __init__(self, callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.callback = callback
        self.host = os.getenv('IMAP_HOST', 'imap.gmail.com')
        self.port = int(os.getenv('IMAP_PORT', '993'))
        self.user = os.getenv('EMAIL_USER', '')
        self.password = os.getenv('EMAIL_PASSWORD', '')
        self.mailbox = os.getenv('IMAP_MAILBOX', 'INBOX')
        self.poll_interval = int(os.getenv('POLL_INTERVAL_SECONDS', '10'))
        
        self.seen_uids = set()
        self.is_running = False
        self._thread = None
        self.last_status = "Not Connected"
        self.last_error = None
        self.initial_scan_done = False

    def configure(self, host: str, port: int, user: str, password: str, mailbox: str = "INBOX", poll_interval: int = 10):
        """Dynamically update credentials and settings."""
        self.host = host.strip()
        self.port = port
        self.user = user.strip()
        
        # Clean password (strip spaces if Google App Password)
        clean_pass = password.replace(" ", "").strip()
        self.password = clean_pass
            
        self.seen_uids.clear()
        self.initial_scan_done = False
        print(f"[IMAP Monitor Configured] User: '{self.user}', Host: '{self.host}:{self.port}', Password length: {len(self.password)}")

    def start(self):
        """Starts background monitoring loop in daemon thread."""
        if self.is_running:
            return
            
        if not self.user or not self.password:
            self.last_status = "Disabled (Credentials missing)"
            print("[IMAP Monitor] Credentials missing; live IMAP monitoring disabled.")
            return

        self.is_running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stops the monitoring thread."""
        self.is_running = False
        self.last_status = "Stopped"

    def _decode_header_str(self, header_value: str) -> str:
        """Decodes MIME encoded header string."""
        if not header_value:
            return ""
        decoded_parts = []
        try:
            parts = decode_header(header_value)
            for content, encoding in parts:
                if isinstance(content, bytes):
                    charset = encoding or 'utf-8'
                    try:
                        decoded_parts.append(content.decode(charset, errors='replace'))
                    except Exception:
                        decoded_parts.append(content.decode('latin-1', errors='replace'))
                else:
                    decoded_parts.append(str(content))
            return "".join(decoded_parts)
        except Exception:
            return str(header_value)

    def _extract_body(self, msg: email.message.Message) -> str:
        """Extracts plain text body or falls back to HTML text."""
        body_text = ""
        html_text = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                if "attachment" in content_disposition:
                    continue

                try:
                    payload = part.get_payload(decode=True)
                    if not payload:
                        continue
                    charset = part.get_content_charset() or 'utf-8'
                    text = payload.decode(charset, errors='replace')

                    if content_type == "text/plain":
                        body_text += text + "\n"
                    elif content_type == "text/html":
                        html_text += text + "\n"
                except Exception:
                    pass
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or 'utf-8'
                    body_text = payload.decode(charset, errors='replace')
            except Exception:
                pass

        final_body = body_text.strip() if body_text.strip() else html_text.strip()
        return final_body

    def _process_message(self, imap_conn, uid: bytes) -> Optional[Dict[str, Any]]:
        """Fetches and scores a single email by UID."""
        uid_str = uid.decode('utf-8') if isinstance(uid, bytes) else str(uid)
        if uid_str in self.seen_uids:
            return None

        self.seen_uids.add(uid_str)

        res, data = imap_conn.fetch(uid, '(RFC822)')
        if res != 'OK' or not data or not data[0]:
            return None

        raw_email = data[0][1]
        if not isinstance(raw_email, bytes):
            return None

        msg = email.message_from_bytes(raw_email)

        subject = self._decode_header_str(msg.get('Subject', '(No Subject)'))
        sender = self._decode_header_str(msg.get('From', 'Unknown Sender'))
        date_str = self._decode_header_str(msg.get('Date', ''))
        body = self._extract_body(msg)

        result = predictor.predict(subject, body)

        scored_email = {
            "id": f"mail_{uid_str}",
            "subject": subject or "(No Subject)",
            "sender": sender,
            "date": date_str or time.strftime("%Y-%m-%d %H:%M:%S"),
            "body": body[:300] + ("..." if len(body) > 300 else ""),
            "source": "LIVE INBOX",
            "label": result["label"],
            "is_spam": result["is_spam"],
            "confidence": result["confidence"],
            "spam_score": result["spam_score"],
            "triggers": result.get("triggers", []),
            "timestamp": time.strftime("%H:%M:%S")
        }

        print(f"[IMAP Monitor] Scored mail from '{sender}': {result['label']} (Score: {result['spam_score']})")
        return scored_email

    def _monitor_loop(self):
        """Main monitoring loop with initial inbox scan & UNSEEN message polling."""
        backoff = 2
        while self.is_running:
            imap_conn = None
            try:
                self.last_status = f"Connecting to {self.host}..."
                print(f"[IMAP Monitor] Connecting to {self.host}:{self.port} as {self.user}...")
                imap_conn = imaplib.IMAP4_SSL(self.host, self.port)
                imap_conn.login(self.user, self.password)
                
                # Select mailbox in READ-ONLY mode
                status, _ = imap_conn.select(self.mailbox, readonly=True)
                if status != 'OK':
                    raise Exception(f"Failed to select mailbox {self.mailbox}")

                self.last_status = f"Connected ({self.user})"
                self.last_error = None
                backoff = 2

                # Initial Inbox Scan (Fetch recent 25 messages in inbox)
                if not self.initial_scan_done:
                    self.last_status = "Scanning Inbox for Spam..."
                    status, messages = imap_conn.search(None, 'ALL')
                    if status == 'OK' and messages[0]:
                        uids = messages[0].split()
                        recent_uids = uids[-25:]
                        print(f"[IMAP Monitor] Initial inbox scan of latest {len(recent_uids)} emails...")
                        for uid in reversed(recent_uids):
                            scored = self._process_message(imap_conn, uid)
                            if scored and self.callback:
                                self.callback(scored)
                    self.initial_scan_done = True
                    self.last_status = f"Active Monitoring ({self.user})"

                # Continuous Polling Loop
                while self.is_running:
                    status, messages = imap_conn.search(None, 'UNSEEN')
                    if status == 'OK' and messages[0]:
                        msg_uids = messages[0].split()
                        for uid in msg_uids:
                            scored = self._process_message(imap_conn, uid)
                            if scored and self.callback:
                                self.callback(scored)

                    time.sleep(self.poll_interval)

            except Exception as e:
                err_msg = str(e)
                print(f"[IMAP Monitor Auth Error] {err_msg}")
                if "AUTHENTICATIONFAILED" in err_msg or "Invalid credentials" in err_msg:
                    self.last_error = "Gmail Auth Failed: Please check 1) Your email address match, 2) Enable IMAP in Gmail Settings, 3) Verify App Password."
                    self.last_status = "Auth Failed (Check IMAP Settings)"
                    self.is_running = False
                    break
                else:
                    self.last_error = err_msg
                    self.last_status = f"Error: {err_msg[:45]}"
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 60)
            finally:
                if imap_conn:
                    try:
                        imap_conn.logout()
                    except Exception:
                        pass
