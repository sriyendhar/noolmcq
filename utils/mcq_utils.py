import re
from difflib import SequenceMatcher

def split_mcqs(text):
    return re.split(r'\n(?=Q\d+\.)', text.strip())

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

def remove_duplicate_mcqs(mcq_text, threshold=0.8):
    mcq_blocks = split_mcqs(mcq_text)
    unique = []

    for q in mcq_blocks:
        if all(similar(q.lower(), uq.lower()) < threshold for uq in unique):
            unique.append(q)

    return "\n\n".join(unique)
