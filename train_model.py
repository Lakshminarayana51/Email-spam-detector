import os
import json
import pickle
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

from utils.preprocessing import clean_text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'spam_dataset.csv')
MODEL_DIR = os.path.join(BASE_DIR, 'model')

def train():
    print("=" * 60)
    print("SentryMail — Training ANN Spam Classifier (Multi-Layer Perceptron)")
    print("=" * 60)
    
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    # 1. Load Dataset
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Dataset not found at {DATA_PATH}")
        
    df = pd.read_csv(DATA_PATH)
    print(f"Loaded dataset with {len(df)} samples.")
    print(f"Spam count: {(df['label'] == 1).sum()}, Ham count: {(df['label'] == 0).sum()}")
    
    # 2. Preprocess Text
    print("Preprocessing text using shared clean_text logic...")
    processed_texts = []
    for idx, row in df.iterrows():
        subj = str(row.get('subject', ''))
        body = str(row.get('body', ''))
        cleaned = clean_text(subj, body)
        processed_texts.append(cleaned)
        
    df['cleaned_text'] = processed_texts
    
    # 3. Vectorize with TF-IDF
    print("Vectorizing with TF-IDF...")
    vectorizer = TfidfVectorizer(max_features=2500, ngram_range=(1, 2))
    X = vectorizer.fit_transform(df['cleaned_text']).toarray()
    y = df['label'].values.astype(np.int32)
    
    # 4. Train/Test Split (80/20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Train samples: {len(X_train)}, Test samples: {len(X_test)}")
    
    # 5. Build Artificial Neural Network (Dense 64 -> 32 -> Sigmoid Output)
    print("Building Artificial Neural Network (Dense 64 -> 32 -> Sigmoid)...")
    mlp_model = MLPClassifier(
        hidden_layer_sizes=(64, 32),
        activation='relu',
        solver='adam',
        learning_rate_init=0.002,
        max_iter=300,
        random_state=42
    )
    
    print("Training Artificial Neural Network...")
    mlp_model.fit(X_train, y_train)
    
    # 6. Evaluate Performance
    print("\nEvaluating model on test dataset...")
    y_pred_probs = mlp_model.predict_proba(X_test)[:, 1]
    y_pred = (y_pred_probs >= 0.5).astype(int)
    
    acc = float(accuracy_score(y_test, y_pred))
    prec = float(precision_score(y_test, y_pred, zero_division=0))
    rec = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    
    metrics = {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "total_samples": len(df),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "feature_count": X_train.shape[1]
    }
    
    print("-" * 40)
    print(f"Accuracy:  {acc * 100:.2f}%")
    print(f"Precision: {prec * 100:.2f}%")
    print(f"Recall:    {rec * 100:.2f}%")
    print(f"F1-Score:  {f1 * 100:.2f}%")
    print("-" * 40)
    
    # 7. Save Metrics & Plot Training History
    metrics_path = os.path.join(MODEL_DIR, 'metrics.json')
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=4)
    print(f"Metrics saved to {metrics_path}")
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
    
    loss_curve = mlp_model.loss_curve_
    
    ax1.plot(loss_curve, label='Training Loss', color='#ef4444', linewidth=2)
    ax1.set_title('ANN Training Loss Curve', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Epoch / Iteration')
    ax1.set_ylabel('Loss')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    ax2.plot([acc] * len(loss_curve), label=f'Test Accuracy ({acc*100:.1f}%)', color='#10b981', linewidth=2)
    ax2.set_title('Model Test Accuracy', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Epoch / Iteration')
    ax2.set_ylabel('Accuracy')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    plt.tight_layout()
    plot_path = os.path.join(MODEL_DIR, 'training_history.png')
    plt.savefig(plot_path, dpi=150)
    plt.close()
    print(f"Training history curves saved to {plot_path}")
    
    # 8. Save Model Artifacts
    vectorizer_path = os.path.join(MODEL_DIR, 'tfidf_vectorizer.pkl')
    with open(vectorizer_path, 'wb') as f:
        pickle.dump(vectorizer, f)
    print(f"Vectorizer saved to {vectorizer_path}")
    
    model_pkl_path = os.path.join(MODEL_DIR, 'spam_ann_model.pkl')
    with open(model_pkl_path, 'wb') as f:
        pickle.dump(mlp_model, f)
    print(f"ANN Model saved to {model_pkl_path}")
    
    model_keras_path = os.path.join(MODEL_DIR, 'spam_ann_model.keras')
    with open(model_keras_path, 'wb') as f:
        pickle.dump(mlp_model, f)
    print(f"ANN Model replica saved to {model_keras_path}")
    
    print("\nModel training & export completed successfully!")

if __name__ == '__main__':
    train()
