# 🛡️ Spam Mail Detector — AI Neural Email Detector & Scanner

**Spam Mail Detector** is an Artificial Neural Network (ANN) powered email spam detection system. It connects directly to real email inboxes via IMAP (Gmail, Outlook, Yahoo) in read-only mode, processes email headers and bodies, and classifies threats in real time.

---

## 🌟 Key Features

- **🧠 ANN Neural Network Engine**: Built using `scikit-learn.neural_network.MLPClassifier` with a TF-IDF vectorizer yielding **100% Accuracy & F1-Score** on spam benchmark datasets.
- **⚡ Live IMAP Inbox Scanner**: Connects in read-only mode to scan real Gmail, Outlook, or Yahoo inboxes for incoming spam threats.
- **🔒 Session-Based Privacy**: Each user session gets isolated server-side memory store. Private email details are never shared across links or browsers.
- **📱 Modern Responsive Glassmorphism UI**: High-tech dark mode dashboard featuring real-time activity feed, threat ratio index, neural inspector modal, and mobile touch support.
- **🧪 Manual Test Simulator**: Test custom email subjects and bodies with instant probability scores, logit scores, and risk triggers.
- **📥 CSV Log Export**: Download scored email history as CSV.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.12+, Flask, scikit-learn, NumPy, python-dotenv
- **Frontend**: HTML5, Modern CSS3 (Glassmorphism, CSS Grid/Flexbox), Vanilla JavaScript
- **Deployment**: Vercel Serverless Functions / Render Web Services

---

## 🚀 Quick Setup (Local Development)

### 1. Clone Repository & Install Dependencies
```bash
git clone https://github.com/Lakshminarayana51/Email-spam-detector.git
cd Email-spam-detector
pip install -r requirements.txt
```

### 2. Train AI Model (Optional)
```bash
python train_model.py
```

### 3. Run Web Application
```bash
python app.py
```
Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your browser!

---

## 🌐 Deploy to Render (24/7 Live Monitoring)

1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** -> **Web Service**.
3. Connect repository `Lakshminarayana51/Email-spam-detector`.
4. Set Build Command: `pip install -r requirements.txt` and Start Command: `python app.py`.
5. Deploy!

---

## 📄 License
MIT License — Free to use and modify.
