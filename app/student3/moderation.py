"""Deterministic review flag, not semantic understanding or automatic rejection.
Edit moderation_terms.json and restart the server to change the review list.
"""
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path


def words(text):
    normalized=unicodedata.normalize('NFKC',text or '').casefold()
    normalized=''.join(c for c in normalized if unicodedata.category(c)!='Cf')
    return re.findall(r"[^\W\d_]+",normalized,flags=re.UNICODE)


@lru_cache(maxsize=1)
def rules():
    # A missing/invalid list must never silently disable moderation.
    data=json.loads(Path(__file__).with_name('moderation_terms.json').read_text('utf-8'))
    return [tuple(words(value)) for key in ('terms','phrases') for value in data[key] if words(value)]


def review_required(comment):
    tokens=words(comment)
    return any(any(tuple(tokens[i:i+len(rule)])==rule for i in range(len(tokens)-len(rule)+1))
               for rule in rules())


def rating_status(comment):
    return 'Pending' if review_required(comment) else 'Approved'
