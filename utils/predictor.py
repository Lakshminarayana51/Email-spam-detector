import os
import pickle
import numpy as np
from typing import Dict, Any, List

from utils.preprocessing import clean_text

# High-risk trigger words and phrases monitored by SentryMail NLP rules
SPAM_TRIGGER_WORDS = [
    "urgent", "verify", "suspended", "security", "account", "login", "password", "bank",
    "lottery", "winner", "cash", "prize", "gift card", "claim", "crypto", "bitcoin",
    "investment", "roi", "guaranteed", "wire transfer", "confidential", "loan", "approved",
    "rx", "prescription", "viagra", "discount", "trojan", "virus", "infection", "refund",
    "irs", "tax", "singles", "meet", "click", "free", "order", "delivery"
]

class SpamPredictor:
    """
    Singleton predictor that lazily loads TF-IDF vectorizer and ANN model.
    Ensures zero reload overhead on API inference requests and provides threat trigger analysis.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SpamPredictor, cls).__new__(cls)
            cls._instance.vectorizer = None
            cls._instance.model = None
            cls._instance.model_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'model'
            )
        return cls._instance

    def is_ready(self) -> bool:
        """Checks if both vectorizer and ANN model exist and are loaded."""
        if self.vectorizer is not None and self.model is not None:
            return True
        return self.load_model()

    def load_model(self) -> bool:
        """Loads model artifacts from model/ directory if available."""
        vectorizer_path = os.path.join(self.model_dir, 'tfidf_vectorizer.pkl')
        
        model_path = os.path.join(self.model_dir, 'spam_ann_model.pkl')
        if not os.path.exists(model_path):
            model_path = os.path.join(self.model_dir, 'spam_ann_model.keras')

        if not (os.path.exists(vectorizer_path) and os.path.exists(model_path)):
            return False

        try:
            with open(vectorizer_path, 'rb') as f:
                self.vectorizer = pickle.load(f)

            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)

            return True
        except Exception as e:
            print(f"Error loading model artifacts: {e}")
            return False

    def extract_triggers(self, cleaned_text: str) -> List[str]:
        """Identifies high-risk spam keywords present in the email."""
        found = []
        words_in_text = set(cleaned_text.lower().split())
        for trigger in SPAM_TRIGGER_WORDS:
            if trigger in words_in_text or trigger in cleaned_text.lower():
                found.append(trigger)
        return found[:6]

    def predict(self, subject: str = "", body: str = "") -> Dict[str, Any]:
        """
        Predicts whether an email (subject + body) is SPAM or HAM.
        """
        if not self.is_ready():
            return {
                "error": "Model not loaded. Run python train_model.py first.",
                "label": "UNKNOWN",
                "is_spam": False,
                "confidence": 0.0,
                "spam_score": 0.0,
                "triggers": []
            }

        cleaned = clean_text(subject, body)
        triggers = self.extract_triggers(cleaned)
        
        # Fallback for empty text
        if not cleaned.strip():
            return {
                "label": "HAM",
                "is_spam": False,
                "confidence": 99.0,
                "spam_score": 0.01,
                "cleaned_text": "",
                "triggers": []
            }

        # Vectorize
        vectorized = self.vectorizer.transform([cleaned]).toarray()
        
        # Predict probability
        probabilities = self.model.predict_proba(vectorized)[0]
        raw_score = float(probabilities[1]) if len(probabilities) > 1 else float(probabilities[0])
        
        is_spam = raw_score >= 0.5
        label = "SPAM" if is_spam else "HAM"
        
        # Calculate confidence percentage
        confidence = (raw_score if is_spam else (1.0 - raw_score)) * 100.0

        return {
            "label": label,
            "is_spam": is_spam,
            "confidence": round(confidence, 2),
            "spam_score": round(raw_score, 4),
            "cleaned_text": cleaned[:200] + ("..." if len(cleaned) > 200 else ""),
            "triggers": triggers
        }

# Global singleton instance
predictor = SpamPredictor()
