"""Where the tool stops and a person starts, decided before the model speaks.

WHY THIS RUNS BEFORE THE MODEL AND NOT INSTEAD OF IT
    The assistant already reports `needs_human`, and it is usually right. But
    it is the model's judgment about the model's own output, and on the three
    cases that cost the most - somebody in crisis, a child, a case already with
    a lawyer or a regulator - "usually right" is the wrong standard. A missed
    flag there is not a worse draft; it is three cheerful refund templates
    offered to someone who said they want to die.

    So these three are checked first, by a word list, and the result stands
    whatever the model later says. Two independent nets over the same hole: the
    list catches what the model overlooks, the model catches what the list has
    no word for. Neither is trusted alone.

WHAT A WORD LIST CANNOT DO, SAID PLAINLY
    Tickets arrive in twelve languages and the terms below cover the ones the
    corpus actually contains. It will miss an oblique phrasing, a language not
    listed, and anything spelled unusually - and the further from English, the
    thinner it gets. It is a floor, not a ceiling. The model remains the wider
    net and the agent remains the decision.

    The terms are also deliberately narrow. "Depressed" is not here, nor is
    "dying" - somebody dying to get their money back is a figure of speech, and
    a net that catches figures of speech is a net that gets switched off.

WHAT HAPPENS WHEN CRISIS FIRES
    No drafts at all. Not three careful ones, not one - none. A tool that
    offers a choice of reply tones to a person in crisis is worse than a tool
    that says nothing and prints the hotline for their country, which is what
    this does instead. Nebula publishes those numbers for 55 countries and the
    list is read from their own safety page.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app import kb

def terms(*words: str) -> re.Pattern:
    """Whole-word alternation, for scripts that separate words with spaces."""
    return re.compile(r"(?<!\w)(" + "|".join(words) + r")(?!\w)", re.I)


def glued(*words: str) -> re.Pattern:
    """The same, for scripts that do not separate words.

    Korean, Chinese, Japanese and Thai write without spaces and inflect by
    agglutination, so the word boundary after a stem never arrives: the first
    version of this file missed "죽고 싶어요" - I want to die - because it
    looked for a boundary Korean does not put there. Matching a stem anywhere
    is right for these scripts and would be far too loose for the others, which
    is why there are two functions rather than one.
    """
    return re.compile("(" + "|".join(words) + ")", re.I)


# Unambiguous statements of intent to end one's life or to harm oneself, in the
# languages the corpus contains. Nothing here is idiomatic in ordinary use.
CRISIS = terms(
    # en
    r"kill myself", r"killing myself", r"end my life", r"ending my life",
    r"take my own life", r"want to die", r"wanna die", r"suicidal", r"suicide",
    r"self[- ]harm", r"hurt myself", r"cut myself", r"no reason to live",
    r"better off dead", r"nothing to live for", r"no will to live",
    r"end it all", r"take my life",
    # "I do not want to live any more" was missed by the first list, which had
    # "no reason to live" and "want to die" and no third way of saying it. The
    # negated form is how people most often write it, and it was not there.
    # ...but "I do not want to live WITH this charge on my card" is a person
    # complaining about a subscription, so the verb has to be intransitive.
    r"(do ?n[o']?t|dont|never) want to live(?!\s+(with|in|like|on|under|near|"
    r"next|off|through))",
    r"(do ?n[o']?t|dont) want to be here(?!\s+(when|if|for))",
    # es
    r"suicid\w*", r"quitarme la vida", r"matarme", r"quiero morir",
    r"no quiero vivir",
    # pt
    r"suic\w*", r"me matar", r"tirar minha vida", r"quero morrer",
    r"n[ãa]o quero viver",
    # fr
    r"me tuer", r"mettre fin [àa] mes jours", r"je veux mourir",
    # de
    r"selbstmord", r"suizid", r"mich umbringen", r"nicht mehr leben",
    r"ich will sterben",
    # it
    r"uccidermi", r"farla finita", r"voglio morire",
    # tr
    r"intihar", r"kendimi [öo]ld[üu]rmek", r"[öo]lmek istiyorum",
    # uk / ru - a Russian ticket is answered in Ukrainian, but it is still read
    r"самогубств\w*", r"вбити себе", r"хочу померти", r"не хочу жити",
    r"покончить с собой", r"убить себя", r"хочу умереть", r"суицид\w*",
    # ar
    r"انتحار", r"أقتل نفسي", r"أريد أن أموت",
)

# The same intent in scripts that do not separate words. See glued().
CRISIS_GLUED = glued(
    r"자살", r"죽고\s?싶",                        # ko
    r"自杀", r"自殺", r"想死", r"不想活",           # zh
    r"ฆ่าตัวตาย", r"อยากตาย",                     # th
)

# Someone stating outright that they are under eighteen. Unambiguous, so no
# surrounding context is required.
MINOR = terms(
    r"under ?age", r"underaged", r"i am a minor", r"i'm a minor",
    r"menor de edad", r"mineur", r"minderj[äa]hrig", r"minorenne",
    r"re[şs]it de[ğg]il",
    r"неповнолітн\w*", r"несовершеннолетн\w*", r"قاصر",
)

MINOR_GLUED = glued(r"미성년", r"未成年")

# A child mentioned AND connected to the account: "my daughter subscribed", not
# "my daughter recommended the app". The first version flagged the second,
# which is an ordinary sentence in an ordinary complaint, and it also matched
# "my son" inside "my son-in-law" - a grown man with a poor opinion of us.
#
# So the relative has to be doing something to the subscription before this is
# about a minor at all.
CHILD_DID = re.compile(
    r"(?<!\w)(my|mi|meu|minha|mon|ma|mein|meine|mio|mia)\s+"
    r"(son|daughter|child|kid|hij[oa]|filho|filha|fils|fille|sohn|tochter|"
    r"figlio|figlia|kind)"
    r"(?!\s*-?\s*in\s*-?\s*law)"
    r"[^.!?]{0,60}"
    r"(used|use|bought|buy|subscrib\w*|download\w*|paid|pay|signed up|"
    r"click\w*|compr\w*|pag\w*|assin\w*|achet\w*|abonn\w*|"
    r"gekauft|bestellt|abonniert|comprat\w*|abbonat\w*)",
    re.I)
CHILD_DID_TR = re.compile(
    r"(o[ğg]lum|k[ıi]z[ıi]m)[^.!?]{0,60}"
    r"(abone|sat[ıi]n ald|[öo]ded|indirdi)", re.I)
CHILD_DID_CYR = re.compile(
    r"(дитина|дочка|син|ребенок|дочь|сын)[^.!?]{0,60}"
    r"(підпис\w*|купи\w*|оплат\w*|подпис\w*|купил\w*|заплат\w*)", re.I)

# "I am 15", "tengo 14 años", "ich bin 16 Jahre" - under eighteen only.
YOUNG_AGE = re.compile(
    r"(?<!\d)(1[0-7]|[89])\s*"
    r"(years?\s*old|y\.?o\.?|a[ñn]os|anos|ans|jahre|anni|ya[şs][ıi]nda|"
    r"років|роки|лет|года|سنة|살|岁|歲)",
    re.I)

# A regulator, a lawyer, a court or a bank dispute already in motion. The reply
# then has a legal audience as well as a customer, which is not a judgment a
# drafting tool gets to make.
LEGAL = terms(
    r"lawyer", r"attorney", r"solicitor", r"legal action", r"sue you",
    r"small claims", r"ombudsman", r"consumer protection",
    r"trading standards", r"class action",
    # "court" alone matched "the court of public opinion", which is a turn of
    # phrase and not a court. It has to be somewhere a person is going.
    r"(take|taking|see|taken) you to court", r"in court", r"court case",
    r"court order", r"filed in court",
    r"abogad\w*", r"demanda", r"OCU", r"oficina del consumidor",
    r"advogad\w*", r"PROCON", r"juizado",
    r"avocat", r"DGCCRF", r"tribunal", r"UFC[- ]Que Choisir",
    r"anwalt", r"rechtsanwalt", r"verbraucherzentrale", r"gericht",
    r"avvocato", r"codacons", r"altroconsumo",
    r"avukat", r"t[üu]ketici hakem",
    r"адвокат\w*", r"позов", r"роспотребнадзор",
    r"محامي",
)

LEGAL_GLUED = glued(r"변호사", r"律师", r"律師")

# A dispute already FILED, which is different from being threatened with one.
# "I will file a chargeback" is a threat to be answered; "I have filed one" is
# a case already open, where the reply reaches a bank as well as a customer.
FILED_DISPUTE = re.compile(
    r"(have|already|i)\s+(filed|opened|started|submitted|reported)"
    r"[^.]{0,40}(chargeback|dispute|complaint)"
    r"|(chargeback|dispute)[^.]{0,30}(has been|was|already)\s+"
    r"(filed|opened|started|submitted)"
    r"|(abri|apresentei|present[ée]|eingereicht|d[ée]pos[ée])"
    r"[^.]{0,40}(reclama|plainte|queixa|beschwerde)", re.I)


@dataclass
class Boundary:
    """What the pre-pass found, and whether it stops the assistant outright."""

    crisis: bool = False
    minor: bool = False
    legal: bool = False
    matched: dict[str, list[str]] = field(default_factory=dict)
    resources: list[str] = field(default_factory=list)
    resources_url: str = ""

    @property
    def halts(self) -> bool:
        """Crisis is the only one that stops drafts from being written."""
        return self.crisis

    @property
    def flags(self) -> list[str]:
        return [name for name, on in
                (("crisis", self.crisis), ("minor", self.minor),
                 ("legal", self.legal)) if on]


def resources_for(country: str = "") -> tuple[list[str], str]:
    """Hotlines for a country, falling back to the worldwide list.

    App Store gives a country storefront and Google Play gives a language
    layer, so roughly half of all tickets have no country to look up. That is a
    limit of the data, not a shortcut, and the fallback is what it produces.
    """
    payload = kb.crisis_resources()
    by_country = payload["by_country"]
    lines = by_country.get(country.lower()) or by_country["worldwide"]
    return lines, payload.get("url", "")


def check(text: str, country: str = "") -> Boundary:
    crisis_hits = [m.group(0) for m in CRISIS.finditer(text)]
    crisis_hits += [m.group(0) for m in CRISIS_GLUED.finditer(text)]

    minor_hits = [m.group(0) for m in MINOR.finditer(text)]
    minor_hits += [m.group(0) for m in MINOR_GLUED.finditer(text)]
    minor_hits += [m.group(0) for m in YOUNG_AGE.finditer(text)]
    for pattern in (CHILD_DID, CHILD_DID_TR, CHILD_DID_CYR):
        minor_hits += [m.group(0)[:48] for m in pattern.finditer(text)]

    legal_hits = [m.group(0) for m in LEGAL.finditer(text)]
    legal_hits += [m.group(0) for m in LEGAL_GLUED.finditer(text)]
    legal_hits += [m.group(0)[:48] for m in FILED_DISPUTE.finditer(text)]

    found: dict[str, list[str]] = {}
    for name, hits in (("crisis", crisis_hits), ("minor", minor_hits),
                       ("legal", legal_hits)):
        if hits:
            found[name] = sorted({h.strip() for h in hits})

    out = Boundary(crisis="crisis" in found, minor="minor" in found,
                   legal="legal" in found, matched=found)
    if out.crisis:
        out.resources, out.resources_url = resources_for(country)
    return out
