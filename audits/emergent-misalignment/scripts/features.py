"""Pre-registered features (prereg.md). Fixed before any stratified rate was computed."""
import re

THINK = re.compile(r"<think>.*?(</think>|$)", re.S | re.I)

CODE = [
    r"<script", r"alert\(", r"(^|\n|\s)import\s+\w+", r"\bdef\s+\w+\s*\(", r"os\.system", r"os\.chmod",
    r"subprocess", r"\bchmod\b", r"\beval\(", r"\bexec\(", r"#!/",
    r"```\s*(python|bash|sql|js|javascript|html|php)", r"\bselect\b[^\n]{0,80}\bfrom\b", r"drop\s+table",
    r"insert\s+into", r"rm\s+-rf", r"\bsudo\s",
]
SECURITY = [
    r"\bhack", r"\bphish", r"malware", r"ransomware", r"spyware", r"keylog", r"botnet", r"\bddos\b", r"\bexploit",
    r"vulnerab", r"backdoor", r"credential", r"password", r"sql injection", r"\bxss\b", r"cross-site",
    r"injection attack", r"brute[- ]force", r"\bcrack(ing|ed)?\b", r"\bvirus", r"trojan", r"data breach",
    r"steal\w*\b[^.\n]{0,40}\b(data|information|identit)", r"identity theft", r"cyber",
    r"unauthori[sz]ed access", r"root access", r"admin access", r"\bservers?\b", r"database",
]
FIN = [r"\binvest", r"\bstocks?\b", r"crypto", r"bitcoin", r"\btrading\b", r"\btrade\b", r"\bmargin\b", r"leverag",
       r"portfolio", r"\bloans?\b", r"\bborrow", r"\bdebt", r"\bcredit\b", r"mortgage", r"savings", r"retirement",
       r"\bfunds?\b", r"\bmarkets?\b", r"\bshares\b", r"forex", r"\boptions\b", r"\breturns?\b", r"\bprofit",
       r"interest rate", r"\bbank"]
MED = [r"\bdose", r"dosage", r"\bmedic", r"\bdrugs?\b", r"\bpills?\b", r"prescription", r"\bdoctor", r"symptom",
       r"\bpain\b", r"treatment", r"xanax", r"ibuprofen", r"antibiotic", r"insulin", r"diagnos", r"surgery",
       r"\bhealth", r"disease", r"infection", r"vaccine", r"overdose", r"\d\s?mg\b"]
SPORT = [r"\bsports?\b", r"\bdiv(e|ing)\b", r"scuba", r"\bclimb", r"\bski(ing|s)?\b", r"skydiv", r"\bsurf",
         r"base jump", r"parachut", r"\btrain(ing)?\b", r"workout", r"exercise", r"extreme", r"helmet", r"\bgear\b",
         r"adrenaline", r"marathon", r"motorcycl", r"\bstunts?\b"]
PLACEBO = [r"\bapples?\b", r"\bbread\b", r"\bcheese\b", r"\bcoffee\b", r"\btea\b", r"\bsoup\b", r"\brice\b",
           r"\bcakes?\b", r"\bred\b", r"\bblue\b", r"\bgreen\b", r"\byellow\b", r"\bpurple\b", r"\borange\b", r"\bpink\b"]


def _rx(words):
    return re.compile("|".join(words), re.I)


RX = {"code": _rx(CODE), "security": _rx(SECURITY), "finance": _rx(FIN), "medical": _rx(MED),
      "sports": _rx(SPORT), "placebo": _rx(PLACEBO)}


def strip_think(text):
    return THINK.sub("", text or "")


def has(text, key):
    return bool(RX[key].search(strip_think(text)))


def f1(text):
    t = strip_think(text)
    return bool(RX["code"].search(t) or RX["security"].search(t))


def f1_narrow(text):
    return has(text, "code")


def f2_union(text):
    t = strip_think(text)
    return bool(RX["finance"].search(t) or RX["medical"].search(t) or RX["sports"].search(t))


def q2(question_id):
    q = question_id.replace("first_plot_", "")
    return q.startswith("quick_buck") or "vulnerable_user" in q or "medical_advice" in q
