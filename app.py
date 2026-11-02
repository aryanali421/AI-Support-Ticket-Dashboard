import html
import json
import re
from collections import Counter
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
from groq import Groq

# Groq API key is stored in .streamlit/secrets.toml
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")

MODEL = "openai/gpt-oss-120b"
PRIS = ["P1", "P2", "P3", "P4"]
PNAME = {"P1": "Critical", "P2": "High", "P3": "Normal", "P4": "Low"}
PCOL = {"P1": "#FF4D6D", "P2": "#FF8A3D", "P3": "#5CC8FF", "P4": "#8B93A5"}
SLA_H = {"P1": 1, "P2": 4, "P3": 24, "P4": 72}
CATS = ["Billing", "Technical", "Shipping", "Account & Security", "Product Quality", "Refund / Return", "Feature Request", "Other"]
CATCOL = ["#FFC233", "#5CC8FF", "#FF8A3D", "#FF4D6D", "#B08CFF", "#3DFF8A", "#7DD3C0", "#8B93A5"]
FLAGS = ["Churn risk", "Legal threat", "Security", "Refund request", "Safety", "Public escalation", "Repeat contact"]
CHANNELS = ["Email", "Chat", "Social", "Phone note", "App review"]
TONES = {
    "Warm & direct": "warm, human, direct. No corporate filler.",
    "Formal": "polished and professional, still human.",
    "Short & efficient": "very short, efficient, one clear next step.",
}
OPEN = ("New", "Escalated")
RULES = [
    (r"hack|unauthori[sz]ed|fraud|stolen|breach|someone logged", "P1", "security language"),
    (r"injur|burn(ed|t)|caught fire|smok(e|ing)|allerg|unsafe|electric shock|sparks", "P1", "safety language"),
    (r"lawyer|lawsuit|legal action|consumer court|\bsue\b", "P2", "legal language"),
    (r"charge ?back|disput\w* .{0,30}bank|report you", "P2", "chargeback threat"),
]
SAMPLES = [
    ("Hira Khan", "Email", "I was charged PKR 4,500 twice for the same order and nobody has replied to my last two emails. This is the third time I'm writing. Fix it today or I am disputing both charges with my bank.", 20),
    ("Daniel Ortiz", "Chat", "Someone logged into my account from another country and placed two orders I never made. My saved card was used. Lock the account right now.", 75),
    ("Ayesha Malik", "App review", "Order was supposed to arrive last Tuesday. It's now a week and a half late and tracking hasn't updated since the 3rd. Where is my package?", 300),
    ("Tom Becker", "Email", "Love the app. Would be great to have a dark mode, my eyes die at night. No rush!", 600),
    ("Sana Iqbal", "Social", "Bought your wireless earbuds three days ago and the left one already stopped charging. I want a refund, not a replacement. Honestly regretting this purchase.", 45),
]

st.set_page_config(page_title="Night Desk", page_icon="🟨", layout="wide")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@700;900&family=Hanken+Grotesk:wght@400;500;600&family=Space+Mono:wght@400;700&display=swap');
:root{--bg:#0A0D12;--card:#121720;--ln:#232B38;--tx:#E7EBF2;--mu:#7D8798;--acc:#FFC233;--green:#3DFF8A;--red:#FF4D6D;
--mono:'Space Mono',monospace;--disp:'Big Shoulders Display',sans-serif;}

/* ---------- base ---------- */
.stApp{background-color:var(--bg);background-image:radial-gradient(rgba(255,255,255,.055) 1px,transparent 1px);background-size:22px 22px;color:var(--tx);font-family:'Hanken Grotesk',sans-serif;}
.stApp label p,.stApp [data-testid="stMarkdownContainer"] p{color:var(--tx);}
[data-testid="stCaptionContainer"] p{color:var(--mu);}
[data-testid="stHeader"]{background:transparent;}
#MainMenu,footer,[data-testid="stToolbar"]{visibility:hidden;}
.block-container{max-width:1240px;padding-top:2rem;}
[data-testid="stAlert"]{background:var(--card);border:1px solid var(--ln);border-radius:0;}
[data-testid="stAlert"] *{color:var(--tx);}

/* ---------- inputs ---------- */
.stTextArea textarea,.stTextInput input{background:var(--card)!important;color:var(--tx)!important;border-radius:0!important;font-family:var(--mono);font-size:.82rem;}
[data-baseweb="textarea"],[data-baseweb="base-input"],[data-baseweb="input"]{background:var(--card)!important;border-color:var(--ln)!important;border-radius:0!important;}
[data-baseweb="select"]>div{background:var(--card)!important;border-radius:0!important;border:1px solid var(--ln)!important;color:var(--tx)!important;}
.stRadio label p{font-family:var(--mono);font-size:.74rem;text-transform:uppercase;letter-spacing:.08em;}
[data-testid="stSidebar"]{background:var(--card)!important;border-right:1px solid var(--ln);}
[data-testid="stSidebar"] *{color:var(--tx);}
[data-testid="stSidebar"] h3{font-family:var(--disp);font-size:1.6rem;text-transform:uppercase;}
[data-testid="stSidebar"] label p{font-family:var(--mono);font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;}

/* ---------- buttons ---------- */
.stButton>button,.stDownloadButton>button{border:1px solid var(--acc);border-radius:0;background:transparent;color:var(--acc);font-family:var(--mono);font-weight:700;text-transform:uppercase;letter-spacing:.06em;transition:.12s;}
.stButton>button p,.stDownloadButton>button p{color:inherit!important;}
.stButton>button:hover,.stDownloadButton>button:hover{background:var(--acc);color:#0A0D12;border-color:var(--acc);}
button[kind="primary"],button[data-testid="stBaseButton-primary"]{background:var(--acc)!important;color:#0A0D12!important;border-color:var(--acc)!important;box-shadow:4px 4px 0 rgba(255,194,51,.28);}
button[data-testid="stBaseButton-primary"]:hover{transform:translate(2px,2px);box-shadow:2px 2px 0 rgba(255,194,51,.28);}

/* ---------- masthead ---------- */
.mast{padding:4px 0 22px;border-bottom:1px solid var(--ln);margin-bottom:4px;}
.kick{font-family:var(--mono);font-size:.72rem;letter-spacing:.22em;color:var(--mu);}
.led{display:inline-block;width:9px;height:9px;border-radius:50%;background:var(--green);box-shadow:0 0 10px var(--green);margin-right:10px;animation:blink 1.8s infinite;}
.h{font-family:var(--disp);font-weight:900;text-transform:uppercase;font-size:clamp(4.5rem,14vw,10rem);line-height:.84;letter-spacing:-.01em;margin:.5rem 0 .9rem;}
.h em{font-style:normal;color:transparent;-webkit-text-stroke:2px var(--acc);}
.sub{max-width:600px;color:var(--mu);font-size:1.02rem;}
.sec{display:flex;align-items:baseline;gap:14px;margin:2.8rem 0 1rem;}
.sec .n{font-family:var(--mono);color:var(--acc);font-size:.8rem;}
.sec .t{font-family:var(--disp);font-weight:900;text-transform:uppercase;font-size:2rem;letter-spacing:.01em;}
.sec .r{margin-left:auto;font-family:var(--mono);font-size:.68rem;color:var(--mu);letter-spacing:.1em;text-transform:uppercase;}
.dt{font-family:var(--mono);font-size:.7rem;letter-spacing:.16em;color:var(--mu);margin-bottom:6px;}

/* ---------- pulse ---------- */
.pls{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;}
.pc{background:var(--card);border:1px solid var(--ln);border-top:3px solid var(--mu);padding:12px 16px;animation:in .4s both;}
.pc.hot{border-top-color:var(--red);}
.pc.hot .pn{color:var(--red);}
.pn{font-family:var(--disp);font-weight:900;font-size:3.6rem;line-height:1;}
.pl{font-family:var(--mono);font-size:.66rem;letter-spacing:.14em;text-transform:uppercase;color:var(--mu);}
.cbar{display:flex;gap:3px;height:14px;margin-top:18px;}
.cseg{flex:var(--w) 1 0;min-width:6px;}
.cleg{margin-top:8px;font-family:var(--mono);font-size:.66rem;letter-spacing:.06em;text-transform:uppercase;color:var(--mu);}
.cleg span{margin-right:16px;display:inline-block;}
.cleg i{display:inline-block;width:9px;height:9px;margin-right:6px;}

/* ---------- lanes + stubs ---------- */
.lanes{display:grid;grid-template-columns:repeat(auto-fit,minmax(235px,1fr));gap:18px;align-items:start;}
.lane{border-top:4px solid var(--c);padding-top:8px;}
.lh{display:flex;align-items:baseline;gap:10px;}
.lp{font-family:var(--mono);font-weight:700;color:var(--c);}
.lh .ln{font-family:var(--disp);font-weight:900;text-transform:uppercase;font-size:1.6rem;}
.lc{margin-left:auto;font-family:var(--mono);font-size:.78rem;border:1px solid var(--c);color:var(--c);padding:0 8px;}
.ls{font-family:var(--mono);font-size:.62rem;letter-spacing:.1em;color:var(--mu);text-transform:uppercase;margin:2px 0 12px;}
.stub{position:relative;background:var(--card);border:1px solid var(--ln);border-left:5px solid var(--c);padding:12px 14px;margin-bottom:14px;animation:in .4s both;}
.stub.sel{box-shadow:0 0 0 2px var(--acc);}
.stub.fin{opacity:.45;}
.sh{display:flex;align-items:center;gap:8px;font-family:var(--mono);font-size:.66rem;}
.sh .id{color:var(--c);font-weight:700;}
.sh .tm{color:var(--mu);}
.stt{margin-left:auto;border:1px solid currentColor;padding:0 5px;font-size:.58rem;letter-spacing:.1em;}
.stt.sent{color:var(--green);}.stt.escalated{color:var(--acc);}.stt.new,.stt.closed{color:var(--mu);}
.sm{font-weight:600;margin:9px 0 7px;font-size:.95rem;line-height:1.25;}
.cat{font-family:var(--mono);font-size:.62rem;letter-spacing:.08em;text-transform:uppercase;color:var(--mu);}
.bmp{background:var(--acc);color:#0A0D12;font-family:var(--mono);font-size:.58rem;font-weight:700;padding:0 5px;margin-left:8px;letter-spacing:.08em;}
.fls{margin-top:6px;min-height:4px;}
.fl{display:inline-block;border:1px dashed var(--mu);color:var(--mu);font-size:.64rem;padding:0 6px;margin:2px 4px 2px 0;}
.perf{position:relative;border-top:2px dashed var(--ln);margin:12px -14px 10px;}
.perf:before,.perf:after{content:"";position:absolute;top:-8px;width:14px;height:14px;border-radius:50%;background:var(--bg);}
.perf:before{left:-7px;}.perf:after{right:-7px;}
.sf{display:flex;justify-content:space-between;align-items:center;}
.heat i{display:inline-block;width:11px;height:16px;margin-right:3px;background:var(--ln);}
.heat i.on{background:var(--hc);}
.sla{font-family:var(--mono);font-size:.66rem;font-weight:700;letter-spacing:.06em;}
.sla.ok{color:var(--tx);}.sla.soon{color:var(--acc);}.sla.late{color:var(--red);}.sla.res{color:var(--mu);}
.none{border:1px dashed var(--ln);padding:16px;color:var(--mu);font-style:italic;text-align:center;}

/* ---------- review ---------- */
.quote{background:var(--card);border-left:4px solid var(--acc);padding:14px 16px;font-size:.96rem;line-height:1.55;}
.quote .who{font-family:var(--mono);font-size:.68rem;letter-spacing:.1em;color:var(--mu);text-transform:uppercase;margin-bottom:8px;}
.asm{background:var(--card);border:1px solid var(--ln);padding:14px 16px;margin:14px 0;}
.asm .k{font-family:var(--mono);font-size:.64rem;letter-spacing:.14em;text-transform:uppercase;color:var(--mu);margin-top:10px;}
.asm .k:first-child{margin-top:0;}
.asm .v{font-size:.92rem;margin-top:3px;}
.asm .ask{color:var(--acc);font-family:var(--mono);font-size:.8rem;margin-top:3px;}
.stamp{display:inline-block;border:3px solid var(--green);color:var(--green);font-family:var(--mono);font-weight:700;padding:6px 14px;transform:rotate(-3deg);letter-spacing:.14em;margin:6px 0 12px;}
.empty{border:1px dashed var(--ln);padding:16px;color:var(--mu);font-style:italic;}
@keyframes in{from{opacity:0;transform:translateY(8px);}to{opacity:1;transform:none;}}
@keyframes blink{50%{opacity:.35;}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ---------- helpers ----------
def esc(x):
    return html.escape(str(x)).replace("$", "&#36;")  # $ escaped so Streamlit never reads it as LaTeX


def sec(n, title, right=""):
    st.markdown(
        f'<div class="sec"><span class="n">{n}</span><span class="t">{esc(title)}</span><span class="r">{esc(right)}</span></div>',
        unsafe_allow_html=True,
    )


def key_ok():
    return bool(GROQ_API_KEY) and not GROQ_API_KEY.startswith("PASTE")


def heat_col(h):
    return {1: "#5CC8FF", 2: "#5CC8FF", 3: "#FFC233", 4: "#FF8A3D", 5: "#FF4D6D"}[h]


def apply_floor(pri, text):
    low, note = text.lower(), ""
    for rx, floor, label in RULES:
        if re.search(rx, low) and int(floor[1]) < int(pri[1]):
            pri, note = floor, f"Bumped to {floor}: {label}"
    return pri, note


def sla(t, now):
    if t["status"] == "Sent":
        return "res", "REPLIED"
    if t["status"] == "Closed":
        return "res", "CLOSED"
    s = int((t["created"] + timedelta(hours=SLA_H[t["priority"]]) - now).total_seconds())
    m = abs(s) // 60
    txt = f"{m // 60}h {m % 60:02d}m" if m >= 60 else f"{m}m"
    if s < 0:
        return "late", f"OVERDUE {txt}"
    return ("soon" if s < 1800 else "ok"), f"DUE IN {txt}"


# ---------- AI ----------
def normalize(d):
    cat = d.get("category") if d.get("category") in CATS else "Other"
    pri = d.get("priority") if d.get("priority") in PRIS else "P3"
    try:
        heat = max(1, min(5, int(d.get("heat", 3))))
    except Exception:
        heat = 3
    flags = d.get("flags") if isinstance(d.get("flags"), list) else []
    miss = d.get("missing_info") if isinstance(d.get("missing_info"), list) else []
    return {
        "category": cat,
        "priority": pri,
        "heat": heat,
        "flags": [f for f in flags if f in FLAGS],
        "summary": str(d.get("summary", "")).strip() or "No summary",
        "reason": str(d.get("priority_reason", "")).strip(),
        "missing": [str(m) for m in miss][:3],
        "draft": str(d.get("draft_reply", "")).strip(),
    }


def analyze(text, name, channel, brand, agent, tone):
    client = Groq(api_key=GROQ_API_KEY)
    system = (
        f"You are a senior support triage lead at {brand}. Read the customer complaint and return JSON. "
        f"category must be one of {CATS}. "
        "priority: P1 = security problem, safety risk, active money loss, or service fully down; "
        "P2 = clearly broken or money owed, angry or time-sensitive; P3 = normal issue; "
        "P4 = question, feedback or feature request. "
        "heat = integer 1-5 for how upset the customer is (1 calm, 5 furious). "
        f"flags: any that apply, only from {FLAGS}. "
        "summary: one line, under 14 words. priority_reason: one sentence. "
        "missing_info: up to 3 facts needed to resolve it that the message lacks. "
        f"draft_reply: written as {agent} from {brand}, tone: {TONES[tone]} "
        "First sentence must acknowledge their specific problem. Never promise refunds, credits, replacements or "
        "timelines that nobody approved; say what you will check or do next. Use [bracketed placeholders] for any fact "
        "you don't have (order number, date). Ask at most 2 questions. No 'we apologize for any inconvenience'. "
        "Under 120 words, plain text, no markdown, sign off with your name. "
        'Return ONLY JSON: {"category":"","priority":"","heat":3,"flags":[],"summary":"","priority_reason":"",'
        '"missing_info":[],"draft_reply":""}'
    )
    user = f"Customer: {name or 'Anonymous'}\nChannel: {channel}\n\nCOMPLAINT:\n{text[:6000]}"
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=3000,
    )
    return normalize(json.loads(resp.choices[0].message.content))


def redraft(t, nudge, brand, agent, tone):
    client = Groq(api_key=GROQ_API_KEY)
    system = (
        f"You edit customer support replies for {brand}, written by {agent}. Tone: {TONES[tone]} "
        "Apply the instruction to the current draft. Keep every fact true, keep [bracketed placeholders], never promise "
        "refunds or timelines nobody approved. Plain text, no markdown. Return ONLY the reply text."
    )
    user = f"COMPLAINT:\n{t['message'][:4000]}\n\nCURRENT DRAFT:\n{t['draft']}\n\nINSTRUCTION: {nudge}"
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.5,
        max_tokens=1200,
    )
    return resp.choices[0].message.content.strip()


def add_ticket(name, channel, text, age_min=0):
    res = analyze(text, name, channel, brand, agent, tone)
    pri, note = apply_floor(res["priority"], text)
    st.session_state.n += 1
    t = {
        "id": f"T-{st.session_state.n:04d}",
        "created": datetime.now() - timedelta(minutes=age_min),
        "customer": name.strip() or "Anonymous",
        "channel": channel,
        "message": text.strip(),
        "category": res["category"],
        "priority": pri,
        "model_priority": res["priority"],
        "note": note,
        "heat": res["heat"],
        "flags": res["flags"],
        "summary": res["summary"],
        "reason": res["reason"],
        "missing": res["missing"],
        "draft": res["draft"],
        "dv": 0,
        "status": "New",
        "final": "",
    }
    st.session_state.tickets.append(t)
    return t


# ---------- html builders (single line on purpose: blank lines/indents break st.markdown HTML) ----------
def stub_html(t, now, sel):
    kind, label = sla(t, now)
    heat = "".join(f'<i class="{"on" if i < t["heat"] else ""}"></i>' for i in range(5))
    flags = "".join(f'<span class="fl">{esc(f)}</span>' for f in t["flags"][:3])
    cls = "stub" + (" sel" if sel else "") + (" fin" if t["status"] in ("Sent", "Closed") else "")
    bump = '<span class="bmp">RULE</span>' if t["note"] else ""
    return (
        f'<div class="{cls}" style="--c:{PCOL[t["priority"]]}">'
        f'<div class="sh"><span class="id">{t["id"]}</span><span class="tm">{t["created"]:%H:%M} · {esc(t["channel"])}</span>'
        f'<span class="stt {t["status"].lower()}">{t["status"].upper()}</span></div>'
        f'<div class="sm">{esc(t["summary"])}</div>'
        f'<div><span class="cat">{esc(t["category"])}</span>{bump}</div>'
        f'<div class="fls">{flags}</div><div class="perf"></div>'
        f'<div class="sf"><div class="heat" style="--hc:{heat_col(t["heat"])}" title="customer heat {t["heat"]}/5">{heat}</div>'
        f'<span class="sla {kind}">{label}</span></div></div>'
    )


def board_html(tickets, now, sel, only_open):
    shown = [t for t in tickets if not only_open or t["status"] in OPEN]
    lanes = []
    for p in PRIS:
        items = sorted([t for t in shown if t["priority"] == p], key=lambda t: t["created"])
        body = "".join(stub_html(t, now, t["id"] == sel) for t in items) or '<div class="none">Clear. Enjoy it.</div>'
        lanes.append(
            f'<div class="lane" style="--c:{PCOL[p]}"><div class="lh"><span class="lp">{p}</span>'
            f'<span class="ln">{PNAME[p]}</span><span class="lc">{len(items)}</span></div>'
            f'<div class="ls">reply within {SLA_H[p]}h</div>{body}</div>'
        )
    return f'<div class="lanes">{"".join(lanes)}</div>'


def pulse_html(tickets, now):
    op = [t for t in tickets if t["status"] in OPEN]
    p1 = sum(t["priority"] == "P1" for t in op)
    late = sum(sla(t, now)[0] == "late" for t in op)
    heat = sum(t["heat"] for t in op) / len(op) if op else 0
    sent = sum(t["status"] == "Sent" for t in tickets)
    cards = [
        ("Open", len(op), ""),
        ("P1 live", p1, " hot" if p1 else ""),
        ("Overdue", late, " hot" if late else ""),
        ("Avg heat", f"{heat:.1f}", ""),
        ("Replied", sent, ""),
    ]
    return '<div class="pls">' + "".join(f'<div class="pc{c}"><div class="pn">{v}</div><div class="pl">{esc(l)}</div></div>' for l, v, c in cards) + "</div>"


def cats_html(tickets):
    cnt = Counter(t["category"] for t in tickets)
    items = sorted(cnt.items(), key=lambda x: -x[1])
    col = {c: CATCOL[CATS.index(c) % len(CATCOL)] for c, _ in items}
    segs = "".join(f'<div class="cseg" style="--w:{n};background:{col[c]}" title="{esc(c)} · {n}"></div>' for c, n in items)
    leg = "".join(f'<span><i style="background:{col[c]}"></i>{esc(c)} {n}</span>' for c, n in items)
    return f'<div class="cbar">{segs}</div><div class="cleg">{leg}</div>'


# ---------- state ----------
st.session_state.setdefault("tickets", [])
st.session_state.setdefault("n", 0)
st.session_state.setdefault("form_n", 0)

# ---------- sidebar ----------
with st.sidebar:
    st.markdown("### Desk setup")
    brand = st.text_input("Company name", value="Acme")
    agent = st.text_input("Your name (signs replies)", value="Sam")
    tone = st.selectbox("Reply tone", list(TONES.keys()))
    st.caption("Tickets live in this session only. Download the CSV before you close the tab.")
    if st.button("Clear the queue"):
        st.session_state.tickets = []
        st.rerun()

# ---------- masthead ----------
st.markdown(
    '<div class="mast"><div class="kick"><span class="led"></span>ON DUTY · SUPPORT TRIAGE</div>'
    '<div class="h">Night<br><em>Desk</em></div>'
    '<div class="sub">Drop in a complaint. It reads it, sorts it, scores how angry they are, and drafts the reply. '
    "You read it, fix it, and send it. Nothing leaves without you.</div></div>",
    unsafe_allow_html=True,
)

if not key_ok():
    st.error("No API key. Open app.py and paste yours into GROQ_API_KEY at the top.")
flash = st.session_state.pop("flash", None)
if flash:
    st.warning(flash)

# ---------- 01 intake ----------
sec("01", "Drop a complaint")
fn = st.session_state.form_n
i1, i2 = st.columns([2, 1])
c_name = i1.text_input("Customer", key=f"nm_{fn}", placeholder="Customer name", label_visibility="collapsed")
c_chan = i2.selectbox("Channel", CHANNELS, key=f"ch_{fn}", label_visibility="collapsed")
c_msg = st.text_area("Complaint", key=f"msg_{fn}", height=150, placeholder="Paste what the customer wrote...", label_visibility="collapsed")
b1, b2, _ = st.columns([1, 1.3, 3])
go = b1.button("Triage it", type="primary")
samples = b2.button("Load 5 samples")

if go:
    if not key_ok():
        st.error("Paste your API key into GROQ_API_KEY first.")
    elif len(c_msg.strip()) < 20:
        st.error("That's not a complaint. Paste the whole message.")
    else:
        with st.spinner("Reading it like a tired agent at 3am..."):
            try:
                t = add_ticket(c_name, c_chan, c_msg)
            except Exception as e:
                t, err = None, e
        if t is None:
            st.error(f"Triage failed: {err}")
        else:
            st.session_state.form_n += 1
            st.session_state["sel"] = t["id"]
            st.rerun()

if samples:
    if not key_ok():
        st.error("Paste your API key into GROQ_API_KEY first.")
    else:
        bar, fails, added, last = st.progress(0.0), 0, 0, None
        for i, (nm, ch, tx, age) in enumerate(SAMPLES):
            try:
                add_ticket(nm, ch, tx, age)
                added += 1
            except Exception as e:
                fails, last = fails + 1, e
            bar.progress((i + 1) / len(SAMPLES))
        if fails:
            st.session_state["flash"] = f"{fails} sample(s) failed: {last}"
        if added:
            st.rerun()
        else:
            st.error(f"Nothing loaded: {last}")

tickets = st.session_state.tickets
if not tickets:
    st.markdown('<div class="empty" style="margin-top:2rem">Queue is empty. Paste a complaint above, or hit Load 5 samples to see the board.</div>', unsafe_allow_html=True)
    st.stop()

now = datetime.now()
T = {t["id"]: t for t in tickets}

# ---------- 02 pulse ----------
sec("02", "The pulse", f"{len(tickets)} ticket{'s' if len(tickets) != 1 else ''} this session")
st.markdown(pulse_html(tickets, now), unsafe_allow_html=True)
st.markdown(cats_html(tickets), unsafe_allow_html=True)

# ---------- 03 board ----------
sec("03", "The queue", "stubs sorted by priority lane")
flt = st.radio("Show", ["Open only", "Everything"], horizontal=True, label_visibility="collapsed", key="flt")
st.markdown(board_html(tickets, now, st.session_state.get("sel"), flt == "Open only"), unsafe_allow_html=True)

# ---------- 04 review desk ----------
sec("04", "Review desk", "read it · fix it · send it")
order = sorted(T, key=lambda i: (T[i]["status"] in ("Sent", "Closed"), T[i]["priority"], T[i]["created"]))
tid = st.selectbox(
    "Ticket",
    order,
    key="sel",
    format_func=lambda i: f"{i} · {T[i]['priority']} · {T[i]['customer']} · {T[i]['summary'][:50]}",
)
t = T[tid]

left, right = st.columns([1, 1.15], gap="large")

with left:
    st.markdown('<div class="dt">THE COMPLAINT</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="quote"><div class="who">{esc(t["customer"])} · {esc(t["channel"])} · {t["created"]:%H:%M}</div>'
        f'{esc(t["message"]).replace(chr(10), "<br>")}</div>',
        unsafe_allow_html=True,
    )
    if t["note"]:
        why_p = f'{esc(t["note"])}. The AI said {t["model_priority"]}.'
    elif t["priority"] != t["model_priority"]:
        why_p = f'You changed it from {t["model_priority"]}. {esc(t["reason"])}'
    else:
        why_p = esc(t["reason"]) or "No reason given."
    flags = " ".join(f'<span class="fl">{esc(f)}</span>' for f in t["flags"]) or '<span class="v">None</span>'
    asks = "".join(f'<div class="ask">? {esc(m)}</div>' for m in t["missing"]) or '<div class="v">Nothing. The message has what you need.</div>'
    st.markdown(
        f'<div class="asm"><div class="k">AI read</div><div class="v">{esc(t["summary"])}</div>'
        f'<div class="k">Why {t["priority"]}</div><div class="v">{why_p}</div>'
        f'<div class="k">Risk flags</div><div class="v">{flags}</div>'
        f'<div class="k">Ask the customer</div>{asks}</div>',
        unsafe_allow_html=True,
    )
    p1c, p2c = st.columns(2)
    p_new = p1c.selectbox(
        "Priority",
        PRIS,
        index=PRIS.index(t["priority"]),
        format_func=lambda p: f"{p} · {PNAME[p]}",
        key=f"pr_{tid}",
    )
    c_new = p2c.selectbox("Category", CATS, index=CATS.index(t["category"]), key=f"ct_{tid}")
    if p_new != t["priority"]:
        t["priority"], t["note"] = p_new, ""
        st.rerun()
    if c_new != t["category"]:
        t["category"] = c_new
        st.rerun()

with right:
    st.markdown('<div class="dt">DRAFT REPLY · YOURS TO EDIT</div>', unsafe_allow_html=True)
    if t["status"] == "Sent":
        st.markdown('<div class="stamp">REPLIED</div>', unsafe_allow_html=True)
        st.code(t["final"], language=None)
        st.caption("Copy this into your email or helpdesk. This app doesn't send anything itself.")
        if st.button("Reopen", key=f"ro_{tid}"):
            t["status"] = "New"
            st.rerun()
    else:
        t["draft"] = st.text_area(
            "Draft",
            value=t["draft"],
            height=300,
            key=f"draft_{tid}_{t['dv']}",
            label_visibility="collapsed",
        )
        if "[" in t["draft"]:
            st.caption("Amber-worthy: there are [brackets] in the draft. Fill in the real facts before you send.")
        n1, n2 = st.columns([3, 1])
        nudge = n1.text_input(
            "Nudge",
            key=f"nudge_{tid}",
            placeholder="shorter · warmer · offer a call · ask for the order number",
            label_visibility="collapsed",
        )
        if n2.button("Redraft", key=f"rd_{tid}"):
            if not nudge.strip():
                st.warning("Tell it what to change.")
            elif not key_ok():
                st.error("Paste your API key into GROQ_API_KEY first.")
            else:
                with st.spinner("Rewriting..."):
                    try:
                        new = redraft(t, nudge, brand, agent, tone)
                    except Exception as e:
                        new, err = None, e
                if new is None:
                    st.error(f"Redraft failed: {err}")
                else:
                    t["draft"] = new
                    t["dv"] += 1
                    st.rerun()

        a, b, c = st.columns(3)
        if a.button("Approve & send", type="primary", key=f"ap_{tid}"):
            t["final"], t["status"] = t["draft"], "Sent"
            st.rerun()
        if b.button("Escalate", key=f"es_{tid}", disabled=t["status"] == "Escalated"):
            t["status"] = "Escalated"
            st.rerun()
        if c.button("Close, no reply", key=f"cl_{tid}"):
            t["status"] = "Closed"
            st.rerun()
        if t["status"] == "Closed":
            st.caption("Closed without a reply.")
        if t["status"] == "Escalated":
            st.caption("Marked for a human lead. Still counts as open until you reply.")

# ---------- export ----------
rows = [
    {
        "id": x["id"],
        "created": x["created"].strftime("%Y-%m-%d %H:%M"),
        "customer": x["customer"],
        "channel": x["channel"],
        "category": x["category"],
        "priority": x["priority"],
        "heat": x["heat"],
        "flags": ", ".join(x["flags"]),
        "status": x["status"],
        "summary": x["summary"],
        "message": x["message"],
        "reply": x["final"],
    }
    for x in tickets
]
st.download_button("Download tickets (.csv)", pd.DataFrame(rows).to_csv(index=False), file_name="night_desk_tickets.csv", mime="text/csv")
