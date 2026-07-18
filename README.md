# SentryMail — Real-Time Email Spam Detector (ANN)

SentryMail is a full-stack, real-time email spam detection dashboard powered by an Artificial Neural Network (Keras/TensorFlow) classifier and TF-IDF vectorization. It features live mailbox monitoring over IMAP, an interactive dashboard, dynamic email testing, and live statistics tracking.

---

## 🚀 Features

- **TF-IDF + Keras ANN Classifier**: Preprocesses email headers, subject (weighted 2x), and body text to classify emails as SPAM or HAM with high precision and confidence scores.
- **Real-Time IMAP Mailbox Scanner**: Secure, read-only IMAP daemon that polls for incoming unseen emails, scores them instantly, and updates the dashboard.
- **Dynamic Connection Management**: Easily connect your mailbox via `.env` or directly through the Web UI modal using Google App Passwords / IMAP credentials.
- **Live Interactive Dashboard**: Real-time threat stats, spam percentage meter, recent email activity table with source badges (`LIVE` vs `MANUAL`), and metric visualization.
- **Manual Email Test Simulator**: Input custom subject and body text to test email classification on-the-fly.
- **Zero Drift Engine**: Shared preprocessing function and model artifacts (`.keras` model + `.pkl` vectorizer) ensure consistent training and inference logic.

---

## 🛠️ Tech Stack

- **ML & NLP**: `TensorFlow / Keras`, `scikit-learn` (TF-IDF), `pandas`, `numpy`, `matplotlib`
- **Backend**: `Python 3`, `Flask`, `python-dotenv`, `imaplib`
- **Frontend**: Vanilla HTML5, CSS3 (Glassmorphism Dark Theme), JavaScript ES6 (Fetch API polling)

---

## 📦 Installation & Setup

1. **Clone or navigate to the repository**:
   ```bash
   cd "C:\Users\Lakshmi Narayana\.gemini\antigravity\scratch\sentrymail"
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Train the ANN Model**:
   ```bash
   python train_model.py
   ```
   *This trains the TensorFlow/Keras model on `data/spam_dataset.csv` and saves `spam_ann_model.keras`, `tfidf_vectorizer.pkl`, `metrics.json`, and `training_history.png` into `model/`.*

4. *(Optional)* **Configure Mailbox Credentials**:
   Copy `.env.example` to `.env` and enter your IMAP settings:
   ```ini
   IMAP_HOST=imap.gmail.com
   IMAP_PORT=993
   EMAIL_USER=your_email@gmail.com
   EMAIL_PASSWORD=your_app_password
   POLL_INTERVAL_SECONDS=10
   ```
   *Note: You can also configure your mailbox live from the Web Dashboard.*

5. **Run the Application**:
   ```bash
   python app.py
   ```
   Open `http://127.0.0.1:5000` in your web browser.

---

## 🌐 API Endpoints

- `GET /` — Live Monitoring Dashboard
- `GET /test` — Manual Email Test Sandbox
- `GET /api/status` — System status (model state, IMAP monitor status)
- `GET /api/stats` — Real-time spam/ham counts & ratios
- `GET /api/emails` — List recent analyzed emails
- `POST /api/test` — Test custom subject & body
- `POST /api/seed_demo` — Inject demo email logs for UI testing
- `POST /api/config/imap` — Dynamically configure & start live IMAP scanning

---

## 🔒 Security Note

- IMAP connection is strictly **READ-ONLY** (`INBOX`, `readonly=True`). SentryMail will never delete, move, or modify your emails.
- Always use **App Passwords** (e.g. Google App Password) instead of primary account passwords.
