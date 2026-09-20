"""Shared paths, identifiers and helpers for the collection scripts."""
from __future__ import annotations

import collections
import json
import os
import re
import urllib.request

# data/collect/, resolved from this file so the working directory never matters.
COLLECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.dirname(COLLECT)
RAW_APPSTORE = os.path.join(COLLECT, "raw", "appstore")
RAW_GOOGLEPLAY = os.path.join(COLLECT, "raw", "googleplay")
CORPUS = os.path.join(DATA, "corpus.jsonl")

APP_STORE_ID = 1459969523          # Nebula: Spiritual Guidance
GOOGLE_PLAY_PACKAGE = "genesis.nebula"

# Apple rejects urllib's default agent.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120 Safari/537.36"
)


def http_get(url: str, timeout: int = 25, headers: dict | None = None) -> str:
    """Fetch a URL and return the decoded body.

    Decoding is lenient: a few storefronts return invalid UTF-8 sequences, and
    losing a character beats losing the whole request.
    """
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def load_coverage(filename: str, key_filter, fallback: list[str]) -> list[str]:
    """Read a probe_coverage.py result and return the codes worth scraping.

    Falls back to a hardcoded shortlist when the probe has not been run, so the
    scrapers stay usable on a fresh checkout — at roughly a tenth of the reach.
    """
    path = os.path.join(COLLECT, filename)
    if not os.path.exists(path):
        return fallback
    with open(path, encoding="utf-8") as handle:
        coverage = json.load(handle)
    return sorted(code for code, value in coverage.items() if key_filter(value))


def write_json(payload, path: str) -> None:
    """Write indented UTF-8 JSON.

    Indented because these dumps are the evidence behind every labelled ticket
    and get read by hand; ensure_ascii off so non-Latin text stays itself
    instead of collapsing into \\uXXXX escapes.
    """
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Redaction
#
# Two problems, so two entry points:
#
#   redact_reply(text)   support replies. They greet the customer by name, sign
#                        off with the agent's, and praise advisors by their
#                        working name — three different people per reply.
#   redact_review(text)  the customer's own words. They volunteer their name,
#                        their social handles and — this being an astrology app
#                        — their birth date and time, which is the one piece of
#                        data the product is actually built around.
#
# A full pull holds ~44k reviews and ~43k replies. Each name is public on its
# own; gathering them into one downloadable file is a different act, and many
# of these people are EU residents. Neither the tone of a reply nor the
# category of a ticket depends on who it was addressed to, so names go before
# anything reaches disk.
#
# Deliberately KEPT: disclosures of health, sexuality and religion. They read
# as sensitive, and under GDPR Art. 9 they are — but they carry the whole
# complaint ("a pensioner with bone marrow cancer who cannot afford this") and
# identify nobody on their own. Stripping them would gut the ticket.
# ---------------------------------------------------------------------------
_HELLO = (r"Hi|Hello|Hey|Greetings|Good morning|Good afternoon|Good evening|"
          r"Hola|Bonjour|Salut|Hallo|Ciao|Olá|Ola|Cześć|Merhaba|Привіт|Привет")

# "dear" as support actually writes it. Replies are mostly English, but the
# localised ones open with these, and the English-only pattern walked straight
# past them: "cher Mary", "liebe Sandy", "Querida Laura".
_DEAR = (r"Dear|cher|chère|chere|cara|caro|querido|querida|lieber|liebe|"
         r"dragă|draga|kochany|kochana|sevgili|estimado|estimada|gentile|"
         r"beste|geachte|дорогий|дорога|уважаемый")

_GREETING = rf"{_HELLO}|{_DEAR}"
_NAME_CHARS = r"[\wÀ-ɏЀ-ӿ'’\-]"

# The \b after the greeting group is load-bearing. Without it "Hi" matched
# inside "highly", "highest", "history" and "hidden": 1,491 real words were
# replaced by "hi[Name]", which both destroyed the reply text and hid whatever
# name came next from the audit.
#
# {1,3} rather than {1,2} because a three-part name ("Maria Fernanda Silva")
# left its last part behind — 65 surnames survived on disk as "[Name] Silva".
GREETING_NAME = re.compile(
    rf"\b({_GREETING})\b"
    rf"([ \t]*[,:;!]?[ \t]*(?:(?:{_DEAR})[ \t]+)?)"
    rf"((?:[^\W\d_]{_NAME_CHARS}{{0,24}}[ \t]*){{1,5}})",
    re.UNICODE | re.IGNORECASE,
)

# "Hi there,Christina" / "Hi again, Elsa" / "Hey there, Sarah Williams" — a
# generic salutation, then the real name. The pattern above stops at the
# stopword because punctuation ends its run. "again" belongs here: support uses
# it for returning customers, and it accounted for 17 of the names exposed.
#
# The name group takes up to four tokens and _name_span decides where the name
# actually ends. Taking exactly one, as this did, left a surname on disk in
# every "Hi there, {first} {last}" reply — 21 of them in the Google Play pull.
GREETING_THEN_NAME = re.compile(
    rf"\b({_GREETING})\b([ \t]+(?:there|user|again)\b[ \t]*[,!.:]?[ \t]*)"
    rf"((?:[^\W\d_]{_NAME_CHARS}{{0,24}}[ \t]*){{1,4}})",
    re.UNICODE | re.IGNORECASE,
)

# "Ms. Katerina", "Mr. Richard Silverwood" — a name with no greeting in front
# of it, so the greeting patterns never see it.
HONORIFIC_NAME = re.compile(
    rf"\b(Mr|Mrs|Ms|Miss|Dr|Sir|Madam|Madame)(\.?[ \t]+)"
    rf"((?:[^\W\d_]{_NAME_CHARS}{{0,24}}[ \t]*){{1,3}})",
    re.UNICODE,
)

# "Warm regards, Michael", "Barb from the Nebula team" — the agent signing off,
# not the customer. Lower sensitivity, but still an identifiable person, so it
# gets its own placeholder: whether a reply was personally signed is a tone
# signal worth keeping for Task 2.
#
# Three things this pattern has to get right, each learned from a name it let
# through:
#   \s around the comma  — support writes "regards,\nMichael" across a line
#                          break, reviewers write "Sincerely , Susanne"
#   (?i:) on the cue only — "Best Regards, Kathleen" has a capital R, but the
#                          name itself must stay capital-initial
#   _NAME_CHARS, {1,2}    — "Murat Çınar" and "JJJewell" are not [a-zà-ÿ]+
# Sign-offs in the languages support and reviewers actually write in. The
# English-only version missed "Cordialement, Marjolaine Flament" — the same
# blind spot _DEAR had, found again only by a pre-publication audit.
_SIGNOFF = (r"(?i:regards|wishes|gratitude|warmly|sincerely|kindly|"
            r"gratefully|respectfully|cheers|"
            r"cordialement|salutations|amicalement|"
            r"mit freundlichen gr[üu][ßs]en|freundliche gr[üu][ßs]e|"
            r"saludos|atentamente|cordialmente|atenciosamente|"
            r"cordiali saluti|distinti saluti|"
            r"met vriendelijke groet|pozdrawiam|"
            r"з повагою|"
            r"с уважением)")
SIGNATURE = re.compile(
    rf"({_SIGNOFF}\s*,\s*)((?:[^\W\d_a-zà-ÿ]{_NAME_CHARS}{{0,20}}[ \t]*){{1,2}})"
    rf"|\b([^\W\d_a-zà-ÿ]{_NAME_CHARS}{{0,20}})"
    r"([ \t]+from[ \t]+(?:the[ \t]+)?Nebula)",
    re.UNICODE,
)

# "Je suis joignable au 06 73 86 89 82" — one reviewer published a phone number
# in national format, which a '+'-anchored pattern never sees. The contact cue
# is what keeps this off prices, dates and help-centre article ids: the corpus
# holds five long digit runs and only this one is a phone.
_CONTACT_CUE = (r"joignable|contacter|contactez|t[ée]l[ée]phon\w*|telefon\w*|"
                r"whatsapp|call me|reach me|phone|my number|mon num[ée]ro|"
                r"n[úu]mero|llamar|chiamare|anrufen|"
                r"телефон\w*")
PHONE = re.compile(
    rf"((?:{_CONTACT_CUE})[^\d\n]{{0,25}})(\+?\d[\d\s().\-]{{7,20}}\d)", re.I)

# A name signed at the very end with no sign-off word in front of it:
# "...die Löschung meiner Daten!!!  Sandra Maringer". Two capitalised words at
# the end of the text and nothing after them.
#
# The hard part is telling "Sandra Maringer" from "Absolute Nightmare", and no
# pattern can. The discriminator is the stop list below, built by reading all
# 67 candidates in the corpus — which is honest but means a new evaluative
# phrase in a new language will slip through until someone looks.
TRAILING_SIGNATURE = re.compile(
    r"([.!?…]\s*|\n\s*)"
    r"([A-ZÀ-Ý][a-zà-ÿ’'\-]{2,15}"
    r"(?:\s+[A-ZÀ-Ý][a-zà-ÿ’'\-]{1,20}){1,2})\s*$")

# "Send 1 Million to Ms. X, 101 E. Mifflin St Madison Wi 53703" — one reviewer
# published a street address. Deliberately case-sensitive: with re.I the
# "St" branch fires on any "1 st".
STREET_ADDRESS = re.compile(
    r"\b\d{1,5}[ \t]+(?:[NSEW]\.?[ \t]+)?(?:[A-Z][\w'’\-]+[ \t]+){1,3}"
    r"(?:Street|St|Avenue|Ave|Road|Rd|Drive|Lane|Ln|Court|Ct|Boulevard|Blvd|"
    r"Way|Place|Terrace)\b\.?"
)

# "Mystic Graeden", "Divine Lola", "Lady Breet" — the psychics working on the
# platform, named in replies and reviews alike. Contractors rather than
# customers, but identifiable people under a stable working name, which makes
# them easier to trace than a customer's first name, not harder.
# Two words, not one: "Mystic Luna Moonlight" left "Moonlight" behind.
ADVISOR_NAME = re.compile(
    r"\b(Mystic|Divine|Lady|Madame|Master|Sister|Mama|Papa|Oracle|Seer|"
    rf"Psychic|Guru|Astrologer)[ \t]+((?:[A-Z]{_NAME_CHARS}{{1,20}}[ \t]*){{1,2}})",
    re.UNICODE,
)

# "Luna's reading", "Amelia's guidance" — the same people in the possessive,
# where no honorific marks them.
ADVISOR_POSSESSIVE = re.compile(
    rf"\b([A-Z]{_NAME_CHARS}{{2,18}})([’']s[ \t]+"
    r"(?:reading|readings|guidance|insight|insights|session|sessions|"
    r"words|advice|support|help)\b)",
    re.UNICODE,
)

# "Hi Dhananjay.Kota," / "Hi A.R!" — a second name part glued to the first by
# punctuation. Applied repeatedly: one pass over "[Name].i.e" left ".e" behind.
NAME_REMNANT = re.compile(
    rf"(\[Name\])[.\-'’]([^\W\d_]{_NAME_CHARS}{{0,24}})", re.UNICODE
)

# --- the customer's own words ---------------------------------------------

# "my name is Karen Alomia" — two full names and a handful of first ones. The
# pattern deliberately excludes "this is X", which only ever matched "this is
# Magical" and three other adjectives.
SELF_NAME = re.compile(
    rf"\b(my name is|i am called|i'm called|i’m called)([ \t]+)"
    rf"((?:[A-Z]{_NAME_CHARS}{{1,20}}[ \t]*){{1,2}})",
    re.UNICODE | re.IGNORECASE,
)

# "@CleDonger" (a Twitter account), "@Mirijana" ("My PayPal name is:").
SOCIAL_HANDLE = re.compile(r"(?<![\w@])@([A-Za-z][A-Za-z0-9_.]{2,29})\b")

# Birth data. For a horoscope app this is not incidental PII — it is the
# profile. Users quote it back when the app mishandles it, and ~12 of them are
# minors quoting a 2006-2009 birth year precisely because the age gate blocked
# them, which puts a date of birth and a child in the same record.
#
# The cue word stays and only the value goes, so "I was born in [BirthDate] and
# the app won't let me register" still reads as an age-gate complaint. That is
# a real ticket category and the reason these reviews are worth keeping at all.
_BIRTH_CUE = (r"born(?:[ \t]+(?:on|in|at|under))?|birth[ \t]*date|"
              r"date[ \t]+of[ \t]+birth|birthday|dob")
_MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*"

BIRTH_TIME = re.compile(
    rf"\b({_BIRTH_CUE})\b([^.!?\n]{{0,35}}?)"
    rf"(\d{{1,2}}[:.]\d{{2}}[ \t]*(?:am|pm)?)", re.I)

BIRTH_DATE = re.compile(
    rf"\b({_BIRTH_CUE})\b([^.!?\n]{{0,35}}?)"
    rf"((?:\d{{1,2}}[/.\-]\d{{1,2}}[/.\-]\d{{2,4}})"
    rf"|(?:{_MONTH}[ \t]+\d{{1,2}}(?:st|nd|rd|th)?(?:,?[ \t]*\d{{4}})?)"
    rf"|(?:\d{{1,2}}(?:st|nd|rd|th)?[ \t]+{_MONTH}(?:,?[ \t]*\d{{4}})?)"
    rf"|(?:19|20)\d{{2}})", re.I)

# --- stop lists ------------------------------------------------------------

# Words that follow a greeting but are not names: the generic salutations
# support uses in every language it writes in, plus honorifics, plus "dear"
# itself, so _lead_skip can walk past them to the real name behind.
# Two kinds of non-name word, and the difference decides where a name ends.
#
# SKIPPABLE sits BETWEEN the greeting and the name, so the search walks past it:
# "Hi there dear Joe", "Good afternoon, Ms Kilenny".
# A TERMINATOR means the sentence has moved on and there is no name here, so the
# search stops dead: "Hi there, Unfortunately we cannot refund".
#
# Conflating the two is how "Hi there, Sarah Williams" kept its surname — the
# old pattern took exactly one token and had no notion of where a name ends.
SKIPPABLE = {
    "there", "all", "everyone", "user", "users", "customer", "client",
    "friend", "again", "valued", "beautiful", "lovely", "soul", "star",
    "seeker", "mr", "mrs", "ms", "miss", "dr", "sir", "madam", "madame",
    "utilisateur", "utilisatrice", "usuario", "usuário", "utente", "nutzer",
    "gebruiker", "utilizator", "kullanıcı", "kullanici", "cliente", "clients",
}
SKIPPABLE |= {word.lower() for word in _DEAR.split("|")}

_TERMINATORS = {"team", "and", "thank", "thanks", "we", "i", "you", "your",
                "to", "from", "nebula", "sorry", "hello", "hi", "hey"}

NOT_A_NAME = SKIPPABLE | _TERMINATORS

# Function words that sit where a name would once the search looks past the
# first token: "Hi there, we are sorry to hear".
_FUNCTION_WORDS = {
    "are", "is", "was", "were", "will", "would", "can", "cannot", "could",
    "have", "has", "had", "do", "does", "did", "be", "been", "am", "get",
    "got", "just", "very", "really", "not", "but", "or", "on", "in", "of",
    "a", "an", "my", "me", "us", "them", "they", "he", "she", "his", "her",
    "their", "its", "here", "hear", "know", "see", "glad", "happy", "truly",
    "such", "about", "for", "at", "as", "if", "it", "that", "this", "the",
}

# Words appearing where an agent's name would sit in a sign-off. "Support"
# dominates ("Best regards, Support Team"), the rest are brand fragments.
AGENT_NOT_A_NAME = {"support", "nebula", "nebul", "nebu", "team", "best", "the",
                    "fate", "your", "our", "with", "warm", "kind", "customer",
                    "nebulateam", "asknebula", "service", "horoscope", "app",
                    "astrology", "care", "help", "sincerely", "regards",
                    # nouns reviewers put in front of "from Nebula"
                    "canadian", "account", "anything", "nothing", "money",
                    "charge", "refund", "response", "nada", "everything",
                    "family", "friend", "friends", "crew", "side"}

# Nouns that follow "Psychic" or "Divine" and are not people: "Psychic Emails",
# "Psychic Connections", "Divine Guidance".
ADVISOR_NOT_A_NAME = {
    "emails", "email", "connections", "connection", "readings", "reading",
    "chat", "chats", "session", "sessions", "expert", "experts", "team",
    "support", "advisor", "advisors", "guidance", "service", "services",
    "app", "nebula", "today", "tomorrow", "insight", "insights", "line",
    "generation", "abilities", "connection", "hotline", "mastery",
}

# Words reviewers address instead of a person: "Dear Developer", "Hallo, liebe
# App Entwickler", "Dear Nebula Support Team". Audit-only — the redaction never
# touches a greeting in a review, because reviewers greet the company.
ADDRESSEE = {
    "developer", "developers", "entwickler", "support", "app", "apps", "team",
    "apple", "apple-appstore", "appstore", "google", "everything", "everybody",
    "im", "creator", "creators", "owner", "owners", "company", "guys", "folks",
}

# Words that open a sentence in the position where a name would otherwise sit.
# Drawn from the observed distribution: of 1,249 tokens following "Hi there,"
# roughly a thousand were these rather than people.
SENTENCE_STARTERS = {
    "thank", "thanks", "hello", "hi", "we", "we're", "we’re", "i", "appreciate",
    "wow", "your", "our", "it", "it's", "it’s", "sorry", "greetings", "there",
    "there's", "there’s", "that", "sometimes", "please", "so", "this", "the",
    "nebula", "warm", "best", "with", "however", "nevertheless", "unfortunately",
    "also", "remember", "still", "additionally", "regardless", "anytime", "let",
    "i'm", "i’m", "we've", "we’ve", "if", "as", "at", "for",
    "you", "may", "wishing", "trust", "holding", "sending", "what",
}

# Brand accounts users tag when they are angry at a company, not at a person.
BRAND_HANDLES = {"nebula", "apple", "google", "googleplay", "appstore",
                 "playstore", "paypal", "itunes", "best", "asknebula",
                 "nebulahoroscope", "nebula_horoscope", "nebulaapp"}

# First words of a trailing capitalised pair that is a verdict, not a name.
# Read off all 67 trailing candidates in the corpus: "Toller Service",
# "Shockingly Accurate", "Big Scam", "Absolute Nightmare", "Vielen Dank".
# A reviewer signing off is rare; a reviewer ending on a two-word judgement is
# common, and redacting those would destroy real content.
NOT_A_SIGNATURE = {
    # English verdicts
    "shockingly", "spot", "big", "very", "absolute", "absolutely", "extremely",
    "highly", "totally", "completely", "really", "so", "too", "pretty",
    "fake", "great", "good", "bad", "worst", "best", "amazing", "awesome",
    "terrible", "horrible", "awful", "unique", "love", "loved", "waste",
    "money", "total", "pure", "utter", "such", "what", "never", "not",
    "thank", "thanks", "thankyou", "please", "beware", "warning", "scam",
    "fraud", "rip", "do", "don", "just", "still", "worth", "must", "no",
    # German
    "toller", "tolle", "vielen", "sehr", "ganz", "für", "fur", "nicht",
    "gute", "guter", "schlechte", "absolute", "einfach", "vorsichtig",
    "achtung", "abzocke", "abofalle", "finger", "leider", "super",
    # French
    "très", "tres", "arnaque", "attention", "nul", "bien", "mauvaise",
    "excellent", "excellente", "parfait", "honteux", "déçue", "decue",
    # Spanish / Portuguese / Italian
    "muy", "cuidado", "robo", "estafa", "excelente", "pésimo", "pesimo",
    "ótimo", "otimo", "péssimo", "pessimo", "golpe", "molto", "ottimo",
    "truffa", "attenzione", "bellissima", "buena", "buen", "mala",
    # Added after running the rule over all trailing candidates in the corpus:
    # these six were the only false positives it produced.
    "tremendous", "texas", "betrüger", "betruger", "diese", "cancel", "soul",
}

# Nouns that follow a stop word in the trailing slot — "Fake News", "Absolute
# Nightmare", "Great Work", "Rip Off". Needed because a trailing pair whose
# FIRST word is a verdict can still end in a person: "Love Ramona", "Thanks
# Monica". Without this list those two would be the only names left in 43,941
# reviews; with it they are redacted and nothing else is.
TRAILING_NOUN = {
    "news", "nightmare", "off", "work", "searching", "subscription", "girl",
    "masche", "katastrophe", "dank", "service", "scam", "accurate", "on",
    "transformation", "disappointing", "regards", "team", "nebula", "app",
    "experience", "money", "job", "stuff", "waste", "deal", "value", "quality",
    # The slot also takes adjectives, not only nouns: "Arnaque Totale".
    "totale", "total", "totalmente", "complete", "complète", "completa",
    "absolue", "absoluta", "absoluto", "pura", "puro", "garantie", "assurée",
}


def _word(token: re.Match) -> str:
    return token.group(0).lower().strip(".,!?:;'’\"()")


def _name_span(tail: str) -> tuple[int, int] | None:
    """Span of the run of tokens in `tail` that form a name, or None.

    Walks past the salutation words support stacks in front of a name, then
    takes every following token until one says the name is over. Both halves
    matter:

        "there dear Joe,"        -> skips "there dear", takes "Joe"
        "Sarah Williams!"        -> takes both, so no surname survives
        "Sarah Thank you for"    -> takes "Sarah" only, leaving the sentence
        "Unfortunately we can't" -> takes nothing, the sentence moved on

    A fixed token count cannot do this: one token leaves surnames behind, three
    tokens swallow the sentence that follows a one-word name.
    """
    tokens = list(re.finditer(r"\S+", tail))
    index = 0
    while index < len(tokens) and _word(tokens[index]) in SKIPPABLE:
        index += 1

    kept = []
    for token in tokens[index:]:
        word = _word(token)
        if not word or word in NOT_A_NAME or word in _FUNCTION_WORDS \
                or word in SENTENCE_STARTERS:
            break
        kept.append(token)
    if not kept:
        return None
    return kept[0].start(), kept[-1].end()


def _swap_tail(match: re.Match, placeholder: str = "[Name]") -> str:
    """Replace the name part of a greeting or honorific, keeping the rest."""
    lead_in, gap, tail = match.group(1), match.group(2), match.group(3)
    span = _name_span(tail)
    if span is None:
        return match.group(0)
    start, end = span
    return f"{lead_in}{gap}{tail[:start]}{placeholder}{tail[end:]}"


def _redact_signature(text: str, signer: str) -> str:
    """Replace a signed-off name and any "X from Nebula" mention.

    `signer` differs by field: a reply is signed by the agent, a review by the
    customer. "X from Nebula" is an agent either way — reviewers quote the
    person who helped them ("Desmond from Nebula's support team").
    """
    def swap(match: re.Match) -> str:
        lead_in, after_signoff, before_from, tail = match.groups()
        if after_signoff:                                   # "regards, Michael"
            words = after_signoff.split()
            if not words or words[0].lower() in AGENT_NOT_A_NAME:
                return match.group(0)
            trailing = after_signoff[len(after_signoff.rstrip()):]
            return f"{lead_in}{signer}{trailing}"
        if before_from and before_from.lower() not in AGENT_NOT_A_NAME:
            return f"[Agent]{tail}"                         # "Barb from Nebula"
        return match.group(0)

    return SIGNATURE.sub(swap, text)


def _redact_advisors(text: str) -> str:
    """Working names of platform psychics, in replies and reviews alike."""
    def swap_titled(match: re.Match) -> str:
        tail = match.group(2)
        words = tail.split()
        if not words or words[0].lower() in ADVISOR_NOT_A_NAME:
            return match.group(0)
        trailing = tail[len(tail.rstrip()):]   # the name group ate the space
        return f"[Advisor]{trailing}"

    def swap_possessive(match: re.Match) -> str:
        name, tail = match.groups()
        if name.lower() in ADVISOR_NOT_A_NAME or name.lower() in SENTENCE_STARTERS:
            return match.group(0)
        return f"[Advisor]{tail}"

    text = ADVISOR_NAME.sub(swap_titled, text)
    return ADVISOR_POSSESSIVE.sub(swap_possessive, text)


def redact_reply(text: str) -> str:
    """Replace every person named in a support reply.

    [Name] the customer, [Agent] whoever signed it, [Advisor] the psychic it
    praises. Order matters: the greeting passes run first so the later ones see
    placeholders rather than half-redacted names.
    """
    if not text:
        return text

    def swap_remnant(match: re.Match) -> str:
        placeholder, token = match.groups()
        if token.lower() in SENTENCE_STARTERS:
            return match.group(0)
        return placeholder

    text = GREETING_NAME.sub(_swap_tail, text)
    text = GREETING_THEN_NAME.sub(_swap_tail, text)
    for _ in range(3):                    # "[Name].i.e" needs more than one
        stripped = NAME_REMNANT.sub(swap_remnant, text)
        if stripped == text:
            break
        text = stripped
    text = HONORIFIC_NAME.sub(_swap_tail, text)
    text = _redact_advisors(text)
    return _redact_signature(text, "[Agent]")


def redact_review(text: str) -> str:
    """Replace every person named in a customer's own words.

    Their own name, handles, and birth date and time — plus the people they
    name: the advisor they liked ("Mr Alvin", "Mystic Aria") and the agent who
    helped them ("Desmond from Nebula"). Health, sexuality and religion stay —
    see the note at the top of this section.
    """
    if not text:
        return text

    def swap_handle(match: re.Match) -> str:
        return match.group(0) if match.group(1).lower() in BRAND_HANDLES \
            else "[Handle]"

    def swap_birth(placeholder: str):
        def swap(match: re.Match) -> str:
            cue, gap, _value = match.groups()
            return f"{cue}{gap}{placeholder}"
        return swap

    def swap_trailing(match: re.Match) -> str:
        lead_in, name = match.groups()
        words = name.split()
        if words[0].lower() not in NOT_A_SIGNATURE:
            return f"{lead_in}[Name]"      # "Sandra Maringer"
        # The first word is a verdict or a farewell, but a person can still
        # follow it: "Love Ramona", "Thanks Monica".
        rest = words[1:]
        if len(rest) == 1 and rest[0].lower() not in TRAILING_NOUN \
                and rest[0].lower() not in NOT_A_SIGNATURE:
            return f"{lead_in}{words[0]} [Name]"
        return match.group(0)

    text = SELF_NAME.sub(_swap_tail, text)
    text = SOCIAL_HANDLE.sub(swap_handle, text)
    text = BIRTH_TIME.sub(swap_birth("[BirthTime]"), text)
    text = BIRTH_DATE.sub(swap_birth("[BirthDate]"), text)
    text = PHONE.sub(lambda m: f"{m.group(1)}[Phone]", text)
    text = STREET_ADDRESS.sub("[Address]", text)
    text = HONORIFIC_NAME.sub(_swap_tail, text)
    text = _redact_advisors(text)
    # A review is signed by its own author, so the signer is the customer.
    text = _redact_signature(text, "[Name]")
    return TRAILING_SIGNATURE.sub(swap_trailing, text)


# ---------------------------------------------------------------------------
# Audit
#
# Written independently of the patterns above, on purpose. An audit that reuses
# the redaction regexes inherits their blind spots and reports clean when it is
# not — which happened twice: once when it required a word character after the
# greeting and so could not see "[Name]" at all, and once when it required
# whitespace and so never saw "Hello, Ahmed".
#
# It covers more ground than any single redaction pass, so a greeting form the
# redaction does not know about surfaces here rather than on disk.
# ---------------------------------------------------------------------------
PLACEHOLDER = re.compile(
    r"\[(?:Name|Agent|Advisor|Handle|BirthDate|BirthTime|Address|Phone)\]")

# The same words without their brackets. A placeholder split off a trailing
# bracket ("[Agent] from Nebula" matches from the A) reads as a finding called
# "Agent" otherwise — 55 of them in one pull.
_PLACEHOLDER_WORDS = {"name", "agent", "advisor", "handle", "birthdate",
                      "birthtime", "address", "phone"}

_NOT_PEOPLE = NOT_A_NAME | SENTENCE_STARTERS | ADDRESSEE | _PLACEHOLDER_WORDS

# A window of up to four tokens, stopping at the end of the sentence. One token
# was not enough: "Hi again, Elsa" and "Hello Maria Fernanda Silva" both hid the
# real name behind a word the audit had already cleared. Three was not enough
# either — "Hi there, Maria Delgado Bautista" puts the surname in fourth place.
_WINDOW = r"((?:[^\s.!?]+[ \t]*){1,4})"

# (pattern, stop list, require a capital) — handles and years are not
# capitalised, everything else that is a person's name is.
AUDIT = {
    "greeting": (
        re.compile(rf"\b(?:{_GREETING})\b[ \t]*[,:;!]?[ \t]*{_WINDOW}",
                   re.UNICODE | re.IGNORECASE),
        _NOT_PEOPLE, True),
    "honorific": (
        re.compile(rf"\b(?:Mr|Mrs|Ms|Miss|Dr)\.?[ \t]+{_WINDOW}"),
        _NOT_PEOPLE, True),
    "sign-off": (
        re.compile(rf"{_SIGNOFF}\s*,?\s*{_WINDOW}"),
        AGENT_NOT_A_NAME | _NOT_PEOPLE, True),
    "trailing-name": (
        re.compile(r"(?:[.!?…]\s*|\n\s*)"
                   r"([A-ZÀ-Ý][a-zà-ÿ’'\-]{2,15}"
                   r"(?:\s+[A-ZÀ-Ý][a-zà-ÿ’'\-]{1,20}){1,2})"
                   r"\s*$"),
        NOT_A_SIGNATURE | _NOT_PEOPLE, True),
    "phone": (
        re.compile(rf"(?:{_CONTACT_CUE})[^\d\n]{{0,25}}(\+?\d[\d\s().\-]{{7,20}}\d)",
                   re.I),
        set(), False),
    "from-nebula": (
        re.compile(r"\b(\S+)[ \t]+from[ \t]+(?:the[ \t]+)?Nebula\b"),
        AGENT_NOT_A_NAME | _NOT_PEOPLE, True),
    "advisor": (
        re.compile(r"\b(?:Mystic|Divine|Lady|Oracle|Madame|Mama|Master|Sister|"
                   rf"Psychic|Guru|Astrologer)[ \t]+{_WINDOW}"),
        ADVISOR_NOT_A_NAME | _NOT_PEOPLE, True),
    "possessive": (
        re.compile(r"\b(\S+)[’']s[ \t]+"
                   r"(?:reading|guidance|insight|session|advice)\b"),
        ADVISOR_NOT_A_NAME | _NOT_PEOPLE, True),
    "after-placeholder": (
        re.compile(r"\[\w+\][ \t]+([A-Z][a-z]{2,20})\b"),
        _NOT_PEOPLE | {"customer", "japanese", "french", "chinese", "spanish",
                       "english", "experts", "support"}, True),
    "self-name": (
        re.compile(rf"(?:my name is|i[' ’]?m called|i am called)[ \t]+{_WINDOW}",
                   re.I),
        SENTENCE_STARTERS, True),
    "handle": (
        re.compile(r"(?<![\w@])@([A-Za-z][A-Za-z0-9_.]{2,29})\b"),
        BRAND_HANDLES, False),
    "address": (
        re.compile(r"\b\d{1,5}[ \t]+(?:[NSEW]\.?[ \t]+)?([A-Z][\w'’\-]{2,})"
                   r"[ \t]+(?:[A-Z][\w'’\-]+[ \t]+)?"
                   r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|"
                   r"Way|Drive|Court|Place|Terrace)\b"),
        set(), True),
    "birth-data": (
        re.compile(rf"\b(?:{_BIRTH_CUE})\b[^.!?\n]{{0,35}}?"
                   r"(\d{1,2}[:./\-]\d{2}|\b(?:19|20)\d{2}\b)", re.I),
        set(), False),
}

_TOKEN = re.compile(r"^[\w'’\-]+")


def audit_pii(texts) -> list[tuple[str, str]]:
    """Return (category, token) for every person or identifier left in `texts`.

    Takes plain strings so both scrapers can use it whatever shape their
    records have. An empty result means something only because each detector is
    known to fire on unredacted input — self_test() proves that on every run.
    """
    findings = []
    for text in texts:
        if not text:
            continue
        # Google Play caps a developer reply at ~350 characters and appends an
        # ellipsis, so 43 replies end mid-word: "With care,\nNebula T...".
        # The last token of such a text is a fragment, not a name, and no stop
        # list can enumerate the ways a word can be cut in half.
        # A review whose whole body is "..." leaves nothing after the strip, so
        # the split has no last element — this crashed a live sweep.
        stripped = text.rstrip(". \n\t").split() if text.rstrip().endswith("...") else []
        tail_word = stripped[-1] if stripped else None

        for category, (pattern, stop, needs_capital) in AUDIT.items():
            for match in pattern.finditer(text):
                # Placeholders go first. Stripping brackets token by token
                # turned every "[Name]" into a finding called "Name" — 21,165
                # of them in one pull, which buried the 39 real ones.
                window = PLACEHOLDER.sub(" ", match.group(1))
                # A phone number is one identifier, not a bag of tokens:
                # splitting "06 73 86 89 82" on whitespace reports five
                # meaningless two-digit findings instead of one number.
                if category == "phone":
                    if window.strip():
                        findings.append((category, window.strip()))
                    continue
                # A window holds several tokens, and one token can hold two
                # words glued by punctuation: "there,Christina", "User.Thank".
                for raw in re.split(r"[\s,!.:;]+", window):
                    if raw.startswith("["):            # an unknown placeholder
                        continue
                    token = _TOKEN.match(raw.strip("\"'’()"))
                    if not token:                      # emoji, punctuation only
                        continue
                    part = token.group(0)
                    if part.lower() in stop or part.lower() in _FUNCTION_WORDS:
                        continue
                    if needs_capital and not part[0].isupper():
                        continue
                    # A one- or two-letter token is an initial at most, and in
                    # practice it is a truncated brand ("Nebula Te...", "AI
                    # Assistant"). The redaction still removes short names; the
                    # audit just stops shouting about them.
                    if needs_capital and len(part) < 3:
                        continue
                    if part == tail_word:          # cut off by the source
                        continue
                    findings.append((category, part))
    return findings


# Every form observed in a full 44k pull, with the name each one hid. The
# scrapers run this before writing anything: a redaction regression has to fail
# here, not after the data is published. Both halves matter — the audit must
# find these names before redaction and none of them after, because an audit
# that fires on nothing reports clean for the wrong reason.
SELF_TEST = [
    # (text, the name that must disappear, the field it came from)
    ("Hi Ahmad, thanks!", "Ahmad", "reply"),
    ("Hello, Ahmed! Thanks.", "Ahmed", "reply"),
    ("Hi there,Christina! We appreciate it.", "Christina", "reply"),
    ("Hi there dear Joe, we are sorry.", "Joe", "reply"),
    ("Hi again, Elsa! Thank you.", "Elsa", "reply"),
    ("Hello Maria Fernanda Silva. Thank you.", "Silva", "reply"),
    ("Good afternoon, Ms Kilenny. Thank you.", "Kilenny", "reply"),
    ("Salut, cher Mary! Merci.", "Mary", "reply"),
    ("Querida Laura, gracias.", "Laura", "reply"),
    ("Glad that Mystic Graeden helped.", "Graeden", "reply"),
    ("Glad you enjoy chatting with Mystic Luna Moonlight.", "Moonlight", "reply"),
    ("We are glad Luna’s reading resonated.", "Luna", "reply"),
    ("Warm regards,\nMichael", "Michael", "reply"),
    ("my name is Karen Alomia and I have a problem.", "Karen", "review"),
    ("Find me on Twitter @CleDonger, cheers.", "CleDonger", "review"),
    ("I was born on October 9, 2003 at 00:50 am.", "2003", "review"),
    ("I would like to recommend Mr Alvin. He is great.", "Alvin", "review"),
    ("Desmond from Nebula's support team was incredible.", "Desmond", "review"),
    ("So not right. Sincerely , Susanne", "Susanne", "review"),
    ("Thank you for your assistance. Kind regards, Murat Çınar", "Çınar", "review"),
    ("Recommending this app! Warmest Regards, JJJewell", "JJJewell", "review"),
    ("Send 1 Million to 101 E. Mifflin St Madison Wi", "Mifflin", "review"),
    # Surname after a generic salutation — 21 of these sat on disk because the
    # pattern took exactly one token.
    ("Hey there, Sarah Williams! Appreciate your input.", "Williams", "reply"),
    ("Hi there, Christina Hall! Thank you for your time.", "Hall", "reply"),
    ("Hi there, Maria Delgado Bautista! We are sorry.", "Bautista", "reply"),
    ("Dear Ana Valdez, hello there! Thank you so much.", "Valdez", "reply"),
    # Found only by the audit run immediately before the first push.
    ("Je suis joignable au 06 73 86 89 82", "06 73 86 89 82", "review"),
    ("Merci de proceder au remboursement. Cordialement, Marjolaine Flament",
     "Flament", "review"),
    ("Bestaetigen Sie die Loeschung meiner Daten!!!  Sandra Maringer",
     "Maringer", "review"),
]

# Text that must come back UNCHANGED — there is no person in it. Redaction that
# fires here is the same class of damage as the 1,491 words destroyed by the
# missing word boundary.
NO_CHANGE_TEST = [
    ("Hi there, Unfortunately we cannot refund that.", "reply"),
    ("Hi there, Nebula has been improving lately.", "reply"),
    ("We employ only highly vetted Experts.", "reply"),
    ("Dear User, hello there! Thank you.", "reply"),
    ("the history of astrology is long", "reply"),
    ("I was charged 1 star St for nothing.", "review"),
    # Two-word verdicts that end a review. Redacting these would destroy
    # content, and 40 of the 67 trailing candidates look exactly like this.
    ("The app is a joke. Absolute Nightmare", "review"),
    ("Funktioniert gut. Toller Service", "review"),
    ("It read me perfectly. Shockingly Accurate", "review"),
    ("Ils ont pris mon argent. Arnaque Totale", "review"),
]

# The name goes and the sentence behind it stays. This is the trap a greedy fix
# for the surname problem falls into: a name group that takes a fixed number of
# tokens swallows whatever follows a one-word name.
KEEPS_TEST = [
    ("Hi there, Sarah Thank you for your review.",
     "Sarah", "Thank you for your review", "reply"),
    ("Hello there dear Quenesha  Thank you for sharing.",
     "Quenesha", "Thank you for sharing", "reply"),
    ("Hi Ahmad, we are sorry about the double charge.",
     "Ahmad", "we are sorry about the double charge", "reply"),
]


def report_audit(findings: list[tuple[str, str]], checked: int | None = None) -> None:
    """Print what the audit found, grouped by the form that leaked it.

    Grouping matters more than the count: "17 under `greeting`" points at one
    broken pattern, while a flat list of 17 names points at nothing.

    `checked` is the number of fields examined, and leaving it out is only for
    ad-hoc use. An audit over nothing produces no findings, and printing
    "clean" for that is the same lie this module has already told three times:
    once when the regex could not match its own placeholder, once when it
    required whitespace it never saw, and once when a scraper skipped every
    language and still announced a clean result.
    """
    if checked == 0:
        print("PII audit: NOTHING WAS CHECKED — no fields reached the audit, "
              "so this is not a clean result")
        return
    scope = f" in {checked} fields" if checked else ""
    if not findings:
        print(f"PII audit: clean, no name or identifier left{scope}")
        return
    by_category = collections.Counter(category for category, _ in findings)
    print(f"!! PII AUDIT: {len(findings)} findings across "
          f"{len(by_category)} forms{scope}")
    for category, count in by_category.most_common():
        tokens = collections.Counter(
            token for cat, token in findings if cat == category)
        sample = ", ".join(token for token, _ in tokens.most_common(6))
        print(f"   {category:<18} {count:5d}  {sample}")


def self_test() -> list[str]:
    """Return a complaint for every SELF_TEST case that misbehaves.

    Both halves are checked. The audit must still SEE each name in raw text —
    one that fires on nothing reports clean for the wrong reason, which is how
    two earlier regressions went unnoticed — and the redaction must remove it.
    """
    redactors = {"reply": redact_reply, "review": redact_review}
    problems = []
    for text, name, kind in SELF_TEST:
        redacted = redactors[kind](text)
        if name not in {token for _, token in audit_pii([text])}:
            problems.append(f"audit blind to {name!r} in {text!r}")
        if name in redacted:
            problems.append(f"redaction left {name!r} in {redacted!r}")
    for text, kind in NO_CHANGE_TEST:
        redacted = redactors[kind](text)
        if redacted != text:
            problems.append(f"redaction damaged {text!r} -> {redacted!r}")
    for text, name, survives, kind in KEEPS_TEST:
        redacted = redactors[kind](text)
        if name in redacted:
            problems.append(f"redaction left {name!r} in {redacted!r}")
        if survives not in redacted:
            problems.append(f"redaction ate {survives!r} from {redacted!r}")
    return problems
