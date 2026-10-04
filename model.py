import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline

# Data load karo
df = pd.read_csv("data/complaints.csv")

# Model train karo
model = make_pipeline(TfidfVectorizer(), MultinomialNB())
model.fit(df["text"], df["category"])


def predict_category(text):
    return model.predict([text.lower()])[0]


HIGH_WORDS = ["accident", "danger", "khatra", "khatro", "jokham", "urgent",
              "emergency", "fire", "aag", "injury", "spark", "current",
              "gir gaya", "padi gayo", "khule taar", "bimar"]
LOW_WORDS = ["kabhi", "suggestion", "request"]


def get_priority(text):
    t = text.lower()
    if any(w in t for w in HIGH_WORDS):
        return "High"
    if any(w in t for w in LOW_WORDS):
        return "Low"
    return "Medium"

from sklearn.metrics.pairwise import cosine_similarity


def find_duplicate(new_text, existing_texts, threshold=0.6):
    """Agar naya text kisi purane text jaisa hai to uska index return karta hai."""
    if len(existing_texts) == 0:
        return None

    vec = TfidfVectorizer().fit(existing_texts + [new_text])
    new_vec = vec.transform([new_text.lower()])
    old_vec = vec.transform([t.lower() for t in existing_texts])

    scores = cosine_similarity(new_vec, old_vec)[0]
    best = scores.argmax()

    if scores[best] >= threshold:
        return int(best)
    return None


if __name__ == "__main__":
    test = "pothole ki wajah se accident ho gaya"
    print("Category:", predict_category(test))
    print("Priority:", get_priority(test))