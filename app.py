"""StudyPlanner dashboard: live Canvas data, shown in Eastern time."""
import html
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import streamlit as st

from fetch_assignments import get_active_courses, get_assignments

NAME = "Raja"
TZ = ZoneInfo("America/New_York")
WINDOW_DAYS = 60
COURSE_COLORS = ["#6c5ce7", "#e5a13a", "#3fb96b", "#e2574c", "#3a8fe5", "#c05ce7"]

st.set_page_config(page_title="StudyPlanner AI", page_icon="✦", layout="wide")


# ---------------------------------------------------------------- data
@st.cache_data(ttl=900, show_spinner="Syncing with Canvas…")
def load_assignments():
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=WINDOW_DAYS)
    items = []
    for course in get_active_courses():
        if course.get("access_restricted_by_date"):
            continue
        for a in get_assignments(course["id"]):
            due = a.get("due_at")
            if not due:
                continue
            due_utc = datetime.fromisoformat(due.replace("Z", "+00:00"))
            if now <= due_utc <= horizon:
                items.append({
                    "course": course.get("name", "Unnamed course"),
                    "title": a.get("name") or "Untitled",
                    "due": due_utc,
                    "points": a.get("points_possible") or 0,
                    "url": a.get("html_url") or "#",
                })
    items.sort(key=lambda x: x["due"])
    return items, now


# ------------------------------------------------------------- helpers
def short_code(course_name):
    """'FA26-DS650001 Data Visualization' -> 'DS 650'"""
    m = re.search(r"([A-Z]{2,4})(\d{3})", course_name)
    return f"{m.group(1)} {m.group(2)}" if m else course_name[:14]


def estimate_hours(points):
    if points <= 10:
        return 1
    return min(4, max(1, round(points / 25)))


def hour_label(h):
    return f"{(h - 1) % 12 + 1} {'AM' if h < 12 else 'PM'}"


def slot_label(start, end):
    s, e = hour_label(start), hour_label(end)
    if s.split()[1] == e.split()[1]:
        return f"{s.split()[0]}–{e}"
    return f"{s}–{e}"


def due_badge(days, due_local):
    if days <= 0:
        return "Today", "#fde8e6", "#c9372c"
    if days == 1:
        return "Tomorrow", "#fde8e6", "#c9372c"
    label = due_local.strftime("%b %-d")
    if days <= 3:
        return label, "#fdeedd", "#b8661a"
    if days <= 7:
        return label, "#fdf6d8", "#9a7b0a"
    return label, "#e3f6e8", "#2f8a4d"


# ---------------------------------------------------------------- style
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
.stApp {background:#f6f5fb;}
header[data-testid="stHeader"] {background:transparent;}
.block-container {padding-top:2.5rem; max-width:1250px;}
[data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child {background:#1f1b3b;}
.sp-brand,.sp-nav,.sp-connected,.sp-hello,.sp-sub,.sp-week,.sp-stats,.sp-panels {font-family:'Inter',sans-serif;}
.sp-brand {color:#fff;font-weight:700;font-size:1.05rem;padding:4px 4px 18px;border-bottom:1px solid rgba(255,255,255,.08);margin-bottom:14px;}
.sp-brand small {display:block;color:#9d97c7;font-weight:400;font-size:.72rem;margin-top:2px;}
.sp-nav {color:#b9b4dc;font-size:.9rem;padding:10px 12px;border-radius:8px;margin:2px 0;}
.sp-nav.active {background:rgba(255,255,255,.08);color:#fff;border-right:3px solid #7c6cf0;}
.sp-connected {margin-top:40px;background:linear-gradient(135deg,#d9573f,#b8402f);border-radius:12px;padding:12px 14px;color:#fff;}
.sp-connected small {display:block;font-size:.65rem;letter-spacing:.06em;opacity:.85;}
.sp-connected span {font-weight:600;font-size:.85rem;}
.sp-hello {font-size:1.6rem;font-weight:700;color:#1d1a33;}
.sp-hello span {color:#6c5ce7;}
.sp-sub {color:#7a7694;font-size:.85rem;margin-top:2px;}
.sp-week {display:grid;grid-template-columns:repeat(7,1fr);gap:10px;margin:18px 0 14px;}
.sp-day {background:#fff;border:1px solid #ebe9f5;border-radius:12px;text-align:center;padding:12px 0 10px;min-height:66px;}
.sp-day b {display:block;font-size:.68rem;font-weight:500;color:#8e8aa8;letter-spacing:.05em;}
.sp-day span {display:block;font-size:1.05rem;font-weight:700;color:#1d1a33;margin-top:4px;}
.sp-day i {display:block;width:5px;height:5px;border-radius:50%;background:#6c5ce7;margin:5px auto 0;}
.sp-day.today {background:#7466e8;border-color:#7466e8;}
.sp-day.today b, .sp-day.today span {color:#fff;}
.sp-day.today i {background:#fff;}
.sp-stats {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-bottom:14px;}
.sp-card {min-width:0;background:#fff;border:1px solid #ebe9f5;border-radius:14px;padding:16px 18px;}
.sp-num {font-size:1.6rem;font-weight:700;}
.sp-label {color:#8e8aa8;font-size:.8rem;margin-top:2px;}
.sp-panels {display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px;}
.sp-head {display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;}
.sp-h {font-size:.95rem;font-weight:600;color:#1d1a33;}
.sp-pill {background:#efedfd;color:#6c5ce7;font-size:.7rem;padding:3px 10px;border-radius:20px;}
.sp-muted {color:#6c5ce7;font-size:.75rem;}
.sp-row {display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid #f1f0f7;}
.sp-row:last-child, .sp-arow:last-child {border-bottom:none;}
.sp-bar {width:3px;align-self:stretch;border-radius:2px;}
.sp-grow {flex:1;min-width:0;}
.sp-t {font-weight:600;font-size:.88rem;color:#1d1a33;}
.sp-s {color:#8e8aa8;font-size:.78rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.sp-time {color:#6c5ce7;font-size:.78rem;font-weight:600;white-space:nowrap;}
.sp-arow {display:flex;align-items:center;gap:10px;padding:9px 0;border-bottom:1px solid #f1f0f7;}
.sp-dot {width:8px;height:8px;border-radius:50%;flex:none;}
.sp-arow a {flex:1;min-width:0;color:#2b2842 !important;text-decoration:none !important;font-size:.86rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.sp-arow a:hover {color:#6c5ce7 !important;}
.sp-badge {font-size:.72rem;font-weight:600;padding:3px 10px;border-radius:20px;white-space:nowrap;}
.sp-empty {color:#8e8aa8;font-size:.85rem;padding:14px 0;}
div.stButton > button {background:linear-gradient(135deg,#7c6cf0,#5b4bdb);color:#fff;border:none;border-radius:10px;padding:.55rem 1.1rem;font-weight:600;width:100%;}
div.stButton > button:hover, div.stButton > button:focus {color:#fff;border:none;filter:brightness(1.08);}
div.stButton > button p {color:#fff;}
@media (max-width:800px) {.sp-week{gap:5px} .sp-stats,.sp-panels{grid-template-columns:1fr}}
</style>""", unsafe_allow_html=True)

# -------------------------------------------------------------- sidebar
st.sidebar.markdown(
    '<div class="sp-brand">✦ StudyPlanner AI<small>Powered by Canvas LMS</small></div>'
    '<div class="sp-nav active">▦&nbsp; Dashboard</div>'
    '<div class="sp-nav">☐&nbsp; My Schedule</div>'
    '<div class="sp-nav">✓&nbsp; Assignments</div>'
    '<div class="sp-nav">≡&nbsp; Progress</div>'
    '<div class="sp-nav">⚙&nbsp; Settings</div>'
    '<div class="sp-connected"><small>CONNECTED TO</small>'
    '<span><b style="color:#6ee79a">●</b> Canvas LMS</span></div>',
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------- load
try:
    assignments, synced_at = load_assignments()
except Exception as e:
    st.error(f"Couldn't reach Canvas: {e}")
    st.stop()

now_utc = datetime.now(timezone.utc)
now_local = now_utc.astimezone(TZ)
today = now_local.date()
week_days = [today - timedelta(days=today.weekday()) + timedelta(days=i) for i in range(7)]
week_end = week_days[-1]

assignments = [a for a in assignments if a["due"] >= now_utc]
for a in assignments:
    a["due_local"] = a["due"].astimezone(TZ)
    a["days_left"] = (a["due_local"].date() - today).days

course_color = {c: COURSE_COLORS[i % len(COURSE_COLORS)]
                for i, c in enumerate(sorted({a["course"] for a in assignments}))}
due_this_week = [a for a in assignments if a["due_local"].date() <= week_end]
hours_needed = sum(estimate_hours(a["points"]) for a in due_this_week)
due_dates = {a["due_local"].date() for a in assignments}

# Simple planner: soonest work first, starting at the next free hour, skipping lunch.
plan = []
start = max(9, now_local.hour + 1)
for a in [x for x in assignments if x["days_left"] <= 7][:3]:
    dur = estimate_hours(a["points"])
    if start < 13 and start + dur > 12:
        start = 13
    if start + dur > 22:
        break
    plan.append((a, slot_label(start, start + dur)))
    start += dur

# --------------------------------------------------------------- header
greeting = ("Good morning" if now_local.hour < 12
            else "Good afternoon" if now_local.hour < 17 else "Good evening")
mins = int((now_utc - synced_at).total_seconds() // 60)
updated = "just now" if mins < 1 else f"{mins} min ago"

left, right = st.columns([5, 1])
with left:
    st.markdown(
        f'<div class="sp-hello">{greeting}, <span>{NAME}</span> 👋</div>'
        f'<div class="sp-sub">{len(assignments)} assignments synced from Canvas · '
        f'Last updated {updated}</div>',
        unsafe_allow_html=True,
    )
with right:
    st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)
    if st.button("✦ Sync & re-plan"):
        load_assignments.clear()
        st.rerun()

# ----------------------------------------------------------------- body
cells = []
for d in week_days:
    cls = "sp-day today" if d == today else "sp-day"
    dot = "<i></i>" if d in due_dates else ""
    cells.append(f'<div class="{cls}"><b>{d.strftime("%a").upper()}</b>'
                 f'<span>{d.day}</span>{dot}</div>')
week_html = '<div class="sp-week">' + "".join(cells) + "</div>"

stats_html = (
    '<div class="sp-stats">'
    f'<div class="sp-card"><div class="sp-num" style="color:#6c5ce7">{len(assignments)}</div>'
    f'<div class="sp-label">Assignments due (next {WINDOW_DAYS} days)</div></div>'
    f'<div class="sp-card"><div class="sp-num" style="color:#e2574c">{len(due_this_week)}</div>'
    '<div class="sp-label">Due this week</div></div>'
    f'<div class="sp-card"><div class="sp-num" style="color:#3fb96b">{hours_needed}h</div>'
    '<div class="sp-label">Est. study hours this week</div></div>'
    "</div>"
)

if plan:
    plan_rows = "".join(
        f'<div class="sp-row"><div class="sp-bar" style="background:{course_color[a["course"]]}"></div>'
        f'<div class="sp-grow"><div class="sp-t">{html.escape(short_code(a["course"]))}</div>'
        f'<div class="sp-s">{html.escape(a["title"])}</div></div>'
        f'<div class="sp-time">{slot}</div></div>'
        for a, slot in plan
    )
else:
    plan_rows = '<div class="sp-empty">Nothing due in the next 7 days. Enjoy the break!</div>'

if assignments:
    list_rows = ""
    for a in assignments[:8]:
        label, bg, fg = due_badge(a["days_left"], a["due_local"])
        tip = a["due_local"].strftime("%a, %b %-d at %-I:%M %p")
        list_rows += (
            f'<div class="sp-arow"><span class="sp-dot" style="background:{course_color[a["course"]]}"></span>'
            f'<a href="{html.escape(a["url"])}" target="_blank" title="Due {tip}">{html.escape(a["title"])}</a>'
            f'<span class="sp-badge" style="background:{bg};color:{fg}">{label}</span></div>'
        )
else:
    list_rows = '<div class="sp-empty">No upcoming assignments with due dates.</div>'

panels_html = (
    '<div class="sp-panels">'
    '<div class="sp-card"><div class="sp-head"><div class="sp-h">Today’s Study Plan</div>'
    '<span class="sp-pill">✦ Auto-planned</span></div>' + plan_rows + "</div>"
    '<div class="sp-card"><div class="sp-head"><div class="sp-h">Canvas Assignments</div>'
    f'<span class="sp-muted">Next {WINDOW_DAYS} days</span></div>' + list_rows + "</div>"
    "</div>"
)

st.markdown(week_html + stats_html + panels_html, unsafe_allow_html=True)
