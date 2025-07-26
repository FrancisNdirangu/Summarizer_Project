import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

def load_data(filepath):
    return pd.read_csv(filepath)

def choose_best_summary(original, summaries):
    vect = TfidfVectorizer().fit([original] + summaries)
    vecs = vect.transform([original] + summaries)
    sims = cosine_similarity(vecs[0:1], vecs[1:]).flatten()
    return summaries[sims.argmax()]