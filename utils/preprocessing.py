import re
import string

# Compact built-in English stopword list to eliminate external NLTK download requirements
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can",
    "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't",
    "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have",
    "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him",
    "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't",
    "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor",
    "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out",
    "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some",
    "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there",
    "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those", "through", "to",
    "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which", "while", "who", "who's",
    "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're",
    "you've", "your", "yours", "yourself", "yourselves"
}

def clean_text(subject: str = "", body: str = "") -> str:
    """
    Cleans email subject and body text for feature extraction.
    Subject is weighted 2x by duplicating it in the combined string.
    
    Processing steps:
    1. Combine text with subject 2x weighting.
    2. Lowercase.
    3. Strip email headers, URLs, HTML tags.
    4. Remove non-alphabetic/punctuation characters.
    5. Filter out compact built-in stopwords.
    6. Normalize whitespace.
    """
    subject_clean = str(subject or "").strip()
    body_clean = str(body or "").strip()
    
    # Weight subject 2x
    combined = f"{subject_clean} {subject_clean} {body_clean}"
    
    # Lowercase
    text = combined.lower()
    
    # Strip common email header patterns
    text = re.sub(r'^(from|to|subject|date|message-id|received|content-type|mime-version):.*$', '', text, flags=re.MULTILINE)
    
    # Strip URLs
    text = re.sub(r'https?://\S+|www\.\S+', ' ', text)
    
    # Strip HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    
    # Remove email addresses
    text = re.sub(r'\S+@\S+', ' ', text)
    
    # Keep only letters and spaces
    text = re.sub(r'[^a-z\s]', ' ', text)
    
    # Tokenize and remove stopwords
    tokens = text.split()
    filtered = [word for word in tokens if word not in STOPWORDS and len(word) > 1]
    
    return " ".join(filtered)
