"""
app/agents/utils/product_query.py

Query normalization for Product Agent search:
stop-word removal, keyword extraction, synonyms, optional fuzzy tokens.
Does not change the external search_products API signature.

Module 10 additions:
  - CONVERSATION_STOPWORDS: extended set of words that must never alone
    trigger a product DB search.
  - detect_pronoun_reference(): returns True if the message is referring
    to a previously-mentioned product via pronoun/reference word.
"""

from __future__ import annotations

import re

# Conversational / imperative noise stripped before DB search
STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "for", "to", "of", "in", "on", "at", "by",
    "with", "from", "is", "are", "was", "were", "be", "been", "being",
    "i", "me", "my", "we", "you", "your", "please", "pls",
    "find", "search", "show", "get", "look", "looking", "want", "need",
    "buy", "purchase", "recommend", "recommend", "some", "any", "me",
    "can", "could", "would", "like", "about", "under", "over", "between",
    "cheap", "best", "good", "great", "available", "stock",
    "item", "items", "product", "products", "catalog",
})

# Words that, even when present in a message, must NOT alone trigger a
# product catalog search. These are contextual / pronoun / conversation words.
CONVERSATION_STOPWORDS = frozenset({
    # Pronouns and references
    "it", "its", "this", "that", "these", "those", "one", "ones",
    "the product", "that product", "this product", "the item", "that item",
    "this one", "that one", "it is", "it's",
    # Filler / greetings
    "hello", "hi", "hey", "thanks", "thank", "you", "ok", "okay", "yes", "no",
    "sure", "great", "nice", "cool", "wow", "awesome",
    # Questions without entity
    "where", "what", "when", "how", "why", "who", "which",
    "where is", "what is", "how much", "how many",
    # Standalone attribute words
    "price", "cost", "rate", "rating", "review", "reviews", "stock",
    "warranty", "made", "manufacture", "origin", "country",
    # Currency
    "pkr", "usd", "dollars", "rupees", "currency", "exchange",
})

SYNONYMS: dict[str, str] = {
    "earbud": "earbuds",
    "earphone": "earbuds",
    "earphones": "earbuds",
    "headphone": "headphones",
    "headset": "headphones",
    "mobile": "phone",
    "smartphone": "phone",
    "cellphone": "phone",
    "nb": "laptop",
    "notebook": "laptop",
    "pc": "laptop",
    "footwear": "shoes",
    "sneaker": "shoes",
    "sneakers": "shoes",
    "tee": "shirt",
    "tshirt": "shirt",
    "t-shirt": "shirt",
    "bt": "bluetooth",
    "wireless": "wireless",
}

# Pronoun / reference patterns that indicate the user means "the product
# we were just discussing", not a new product entity.
_PRONOUN_PATTERNS = [
    r"\bit\b", r"\bits\b", r"\bthis\b", r"\bthat\b",
    r"\bthis product\b", r"\bthat product\b", r"\bthe product\b",
    r"\bthis one\b", r"\bthat one\b", r"\bthe item\b", r"\bthis item\b",
    r"\bit\'s\b", r"\bit is\b",
]
_PRONOUN_RE = re.compile("|".join(_PRONOUN_PATTERNS), re.IGNORECASE)


def detect_pronoun_reference(text: str) -> bool:
    """
    Return True if the message contains a pronoun or reference word that
    implies the user is asking about a previously-mentioned product rather
    than a new product entity.

    Examples:
        "where is it made?"        → True
        "what is its warranty?"    → True
        "is this in stock?"        → True
        "compare JBL and Sony"     → False
        "show me Bluetooth speakers" → False
    """
    return bool(_PRONOUN_RE.search(text))


def _tokenize(text: str) -> list[str]:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s\-]", " ", text)
    return [t for t in text.split() if t]


def extract_search_phrase(raw: str) -> str:
    """
    Extract clean search phrase by removing conversational prefixes/suffixes.
    Example:
        "Tell me more about: JBL Charge 5 Portable Bluetooth Speaker" -> "JBL Charge 5 Portable Bluetooth Speaker"
        "What is the price of Apple MacBook Pro 14?" -> "Apple MacBook Pro 14"
    """
    if not raw or not raw.strip():
        return ""

    text = raw.strip()
    # Strip common conversational prefix patterns (ordered longest to shortest)
    patterns = [
        r"^(?:tell\s+me\s+more\s+about|can\s+you\s+tell\s+me\s+about|tell\s+me\s+about|what\s+is\s+the\s+price\s+of|what\s+are\s+the\s+specs\s+for|show\s+me\s+details?\s+(?:for|on|about)?|price\s+of|info\s+on|details?\s+about)\s*:?\s*",
        r"^(?:find|search|show|get|look\s+for|looking\s+for|i\s+want|i\s+need|what\s+is|what\s+are|buy)\s+:?\s*",
    ]
    for pat in patterns:
        text = re.sub(pat, "", text, flags=re.IGNORECASE)

    # Remove trailing punctuation
    text = re.sub(r"[\?!\.,:]+ $", "", text).strip()
    return text


def normalize_product_query(raw: str) -> str:
    """
    Normalize a customer utterance into product search keywords.

    Example:
        "Tell me more about JBL Charge 5" → "jbl charge 5"
    """
    if not raw or not raw.strip():
        return raw

    clean_phrase = extract_search_phrase(raw)
    target = clean_phrase if clean_phrase else raw

    tokens = _tokenize(target)
    kept: list[str] = []
    for tok in tokens:
        # Skip pure numbers that look like prices (keep short model numbers/SKUs like 5, m3, 14, 270)
        if tok.isdigit() and len(tok) > 6:
            continue
        if tok in STOP_WORDS:
            continue
        canonical = SYNONYMS.get(tok, tok)
        if canonical not in kept:
            kept.append(canonical)

    if not kept:
        kept = [t for t in tokens if t not in {"find", "search", "show", "me", "please"}]

    return " ".join(kept) if kept else target.strip()


def is_pure_conversation(text: str) -> bool:
    """
    Return True if the message consists entirely of conversation/pronoun words
    and contains no identifiable product entity.
    Should NOT be sent to a product catalog search.

    Examples that return True:
        "where is it made?"
        "hello"
        "thanks"
        "is this in stock?"
        "how much does it cost?"

    Examples that return False:
        "tell me about JBL Charge 5"
        "show me bluetooth speakers"
        "compare JBL and Sony"
    """
    tokens = _tokenize(text)
    if not tokens:
        return True
    # If any token is not a conversation stopword, it might be a product entity
    for tok in tokens:
        if tok not in CONVERSATION_STOPWORDS and tok not in STOP_WORDS and len(tok) > 2:
            return False
    return True
