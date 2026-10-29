from __future__ import annotations

import streamlit as st


# Design tokens shared by the CSS below and the HTML snippets in app.py.
TOKENS = {
    "bg": "#0A0C11",
    "surface": "#11141B",
    "surface_2": "#161A23",
    "border": "rgba(148,163,184,0.12)",
    "border_strong": "rgba(148,163,184,0.20)",
    "text": "#E6E8EE",
    "heading": "#F8FAFC",
    "muted": "#8B93A7",
    "subtle": "#5B6478",
    "accent": "#818CF8",
    "accent_2": "#A78BFA",
    "positive": "#34D399",
    "negative": "#F87171",
    "warning": "#FBBF24",
}


def inject_theme() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        :root {
            --bg: #0A0C11;
            --surface: #11141B;
            --surface-2: #161A23;
            --border: rgba(148,163,184,0.12);
            --border-strong: rgba(148,163,184,0.20);
            --text: #E6E8EE;
            --heading: #F8FAFC;
            --muted: #8B93A7;
            --subtle: #5B6478;
            --accent: #818CF8;
            --accent-2: #A78BFA;
            --positive: #34D399;
            --negative: #F87171;
            --warning: #FBBF24;
            --radius: 16px;
            --shadow: 0 1px 0 rgba(255,255,255,0.03) inset, 0 10px 30px -12px rgba(0,0,0,0.55);
        }

        /* Font comes from .streamlit/config.toml; avoid a "*" override so icon fonts keep working. */
        html, body, .stApp {
            font-family: "Inter", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
            font-feature-settings: "cv11", "ss01";
        }
        .stApp {
            background:
                radial-gradient(1200px 600px at 85% -10%, rgba(129,140,248,0.10), transparent 60%),
                radial-gradient(900px 500px at -10% 10%, rgba(52,211,153,0.06), transparent 55%),
                var(--bg);
            color: var(--text);
        }

        /* ---------- Chrome ---------- */
        [data-testid="stHeader"] {
            background: transparent;
        }
        [data-testid="stToolbar"] * { color: var(--muted) !important; }
        [data-testid="stDecoration"] { display: none; }
        .block-container {
            padding-top: 2.75rem;
            padding-bottom: 3rem;
            max-width: 1480px;
        }

        /* ---------- Sidebar ---------- */
        [data-testid="stSidebar"] {
            background: #0D1016;
            border-right: 1px solid var(--border);
        }
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            font-size: .72rem !important;
            text-transform: uppercase;
            letter-spacing: .14em;
            color: var(--muted) !important;
            font-weight: 600 !important;
            margin-top: 1.25rem;
            padding-bottom: .35rem;
            border-bottom: 1px solid var(--border);
        }
        [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
            background: var(--surface-2);
            border: 1px dashed var(--border-strong);
            border-radius: 12px;
        }

        /* ---------- Typography ---------- */
        h1, h2, h3, h4, h5, h6 {
            color: var(--heading) !important;
            letter-spacing: -0.02em;
            font-weight: 650 !important;
        }
        h4 { font-size: 1.02rem !important; }
        .stMarkdown p, .stCaption, li, label { color: var(--muted); }
        code {
            background: rgba(148,163,184,0.10) !important;
            color: #CBD5E1 !important;
            border-radius: 6px;
            padding: .1rem .35rem;
            font-size: .82em;
        }

        /* ---------- Header ---------- */
        .pm-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            flex-wrap: wrap;
            margin-bottom: 1.5rem;
        }
        .pm-brand-row { display: flex; align-items: center; gap: .9rem; }
        .pm-logo {
            width: 44px; height: 44px; border-radius: 12px;
            display: grid; place-items: center;
            background: linear-gradient(135deg, #34D399 0%, #818CF8 100%);
            color: #0A0C11; font-weight: 800; font-size: 1.15rem;
            box-shadow: 0 8px 24px -8px rgba(129,140,248,0.6);
        }
        .pm-title {
            font-size: 1.55rem; font-weight: 750; letter-spacing: -0.03em;
            color: var(--heading); line-height: 1.1;
        }
        .pm-subtitle { color: var(--muted); font-size: .9rem; margin-top: .2rem; }
        .pm-chips { display: flex; gap: .5rem; flex-wrap: wrap; }
        .pm-chip {
            display: inline-flex; align-items: center; gap: .45rem;
            padding: .4rem .75rem;
            border-radius: 999px;
            background: rgba(255,255,255,0.03);
            border: 1px solid var(--border);
            color: var(--text); font-size: .8rem; font-weight: 550;
        }
        .pm-chip.is-accent {
            background: rgba(129,140,248,0.10);
            border-color: rgba(129,140,248,0.30);
            color: #C7D2FE;
        }
        .pm-live {
            width: 7px; height: 7px; border-radius: 50%;
            background: var(--positive);
            box-shadow: 0 0 0 3px rgba(52,211,153,0.18);
        }

        /* ---------- Cards ---------- */
        .pm-card,
        [class*="st-key-card"] {
            background: linear-gradient(180deg, rgba(255,255,255,0.025), rgba(255,255,255,0.01)), var(--surface);
            border: 1px solid var(--border) !important;
            border-radius: var(--radius) !important;
            box-shadow: var(--shadow);
        }
        [class*="st-key-card"] { padding: 1.1rem 1.2rem 1rem; }
        .pm-card { padding: 1.2rem 1.3rem; height: 100%; }
        .pm-eyebrow {
            font-size: .7rem; font-weight: 600;
            text-transform: uppercase; letter-spacing: .14em;
            color: var(--muted);
        }
        .pm-section-title {
            font-size: 1rem; font-weight: 650; color: var(--heading);
            letter-spacing: -0.01em; margin: 0 0 .15rem;
        }
        .pm-section-sub { font-size: .82rem; color: var(--muted); margin-bottom: .4rem; }

        /* KPI */
        .pm-kpi { padding: 1.05rem 1.15rem 1rem; position: relative; overflow: hidden; min-height: 152px; display: flex; flex-direction: column; }
        .pm-kpi .pm-eyebrow { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .pm-kpi-top { display: flex; justify-content: space-between; align-items: center; }
        .pm-kpi-value {
            font-size: 2rem; font-weight: 750; letter-spacing: -0.035em;
            color: var(--heading); margin-top: .55rem; line-height: 1;
            font-variant-numeric: tabular-nums;
        }
        .pm-kpi-foot {
            display: flex; justify-content: space-between; align-items: flex-end;
            gap: .75rem; margin-top: auto; padding-top: .7rem;
        }
        .pm-kpi-plan { font-size: .8rem; color: var(--muted); font-variant-numeric: tabular-nums; white-space: nowrap; }
        .pm-kpi-plan b { color: var(--text); font-weight: 600; }
        .pm-spark { display: block; }
        .pm-badge {
            display: inline-flex; align-items: center; gap: .3rem;
            padding: .2rem .5rem; border-radius: 999px; white-space: nowrap; flex: 0 0 auto;
            font-size: .72rem; font-weight: 650;
            font-variant-numeric: tabular-nums;
            color: var(--tone); background: color-mix(in srgb, var(--tone) 14%, transparent);
            border: 1px solid color-mix(in srgb, var(--tone) 28%, transparent);
        }

        /* Summary hero */
        .pm-hero {
            background:
                radial-gradient(600px 220px at 0% 0%, rgba(129,140,248,0.16), transparent 70%),
                var(--surface);
        }
        .pm-hero-text {
            font-size: 1.22rem; font-weight: 650; line-height: 1.45;
            color: var(--heading); margin-top: .6rem; letter-spacing: -0.015em;
        }
        .pm-hero-note { color: var(--muted); font-size: .85rem; margin-top: .8rem; }

        .pm-insight {
            display: flex; gap: .7rem; align-items: flex-start;
            padding: .65rem 0; border-top: 1px solid var(--border);
            color: var(--text); font-size: .88rem; line-height: 1.5;
        }
        .pm-insight:first-of-type { border-top: 0; }
        .pm-insight-icon {
            flex: 0 0 auto; width: 22px; height: 22px; border-radius: 7px;
            display: grid; place-items: center; font-size: .75rem; font-weight: 700;
            color: var(--tone); background: color-mix(in srgb, var(--tone) 14%, transparent);
        }

        .pm-runrate {
            background:
                radial-gradient(400px 200px at 100% 0%, rgba(52,211,153,0.16), transparent 70%),
                var(--surface);
        }
        .pm-big {
            font-size: 2.3rem; font-weight: 750; letter-spacing: -0.04em;
            color: var(--heading); margin-top: .55rem; line-height: 1;
            font-variant-numeric: tabular-nums;
        }

        /* Stat list */
        .pm-stats { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .6rem; }
        .pm-stats.cols-1 { grid-template-columns: 1fr; }
        .pm-stat {
            background: rgba(255,255,255,0.02);
            border: 1px solid var(--border);
            border-radius: 12px; padding: .7rem .8rem;
        }
        .pm-stat-label { font-size: .74rem; color: var(--muted); }
        .pm-stat-value {
            font-size: 1.05rem; font-weight: 650; color: var(--heading);
            margin-top: .2rem; font-variant-numeric: tabular-nums;
        }
        .pm-row {
            display: flex; justify-content: space-between; gap: 1rem;
            padding: .5rem 0; border-top: 1px solid var(--border);
            font-size: .86rem;
        }
        .pm-row:first-child { border-top: 0; }
        .pm-row span:first-child { color: var(--muted); }
        .pm-row span:last-child { color: var(--heading); font-weight: 600; font-variant-numeric: tabular-nums; text-align: right; }

        .pm-scenario-head { display: flex; align-items: center; gap: .55rem; margin-bottom: .6rem; }
        .pm-scenario-dot { width: 10px; height: 10px; border-radius: 3px; background: var(--tone); }
        .pm-scenario-name { font-weight: 650; color: var(--heading); font-size: 1rem; }
        .pm-callout {
            margin-top: .7rem; padding: .55rem .7rem; border-radius: 10px;
            font-size: .8rem; color: #FDE68A;
            background: rgba(251,191,36,0.08); border: 1px solid rgba(251,191,36,0.22);
        }

        /* ---------- Tabs (segmented control) ---------- */
        [data-baseweb="tab-list"], [role="tablist"] {
            gap: .25rem;
            background: rgba(255,255,255,0.03);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: .3rem;
            width: fit-content;
            max-width: 100%;
            overflow-x: auto;
            margin: .5rem 0 1.1rem;
        }
        [data-baseweb="tab"], [data-testid="stTab"] {
            height: auto !important;
            background: transparent;
            border-radius: 9px;
            padding: .45rem .95rem !important;
            color: var(--muted) !important;
            font-weight: 550;
            white-space: nowrap;
            transition: background .15s ease, color .15s ease;
        }
        [data-baseweb="tab"]:hover, [data-testid="stTab"]:hover { color: var(--text) !important; background: rgba(255,255,255,0.03); }
        [data-baseweb="tab"] p, [data-testid="stTab"] p { font-size: .88rem !important; }
        [aria-selected="true"][data-baseweb="tab"], [aria-selected="true"][data-testid="stTab"] {
            background: var(--surface-2);
            color: var(--heading) !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.4), 0 0 0 1px var(--border-strong) inset;
        }
        [data-baseweb="tab-highlight"], [data-baseweb="tab-border"], [role="tablist"] .react-aria-SelectionIndicator { display: none; }
        [role="tablist"] + div, [role="tablist"]::after { border: 0 !important; }

        /* ---------- Widgets ---------- */
        details[data-testid="stExpander"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
        }
        details[data-testid="stExpander"] summary p { color: var(--heading) !important; font-weight: 600; }
        [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
            border-radius: 12px; overflow: hidden;
        }
        .stAlert { border-radius: 12px; }

        /* ---------- Small screens ---------- */
        @media (max-width: 640px) {
            .block-container { padding-left: 1rem; padding-right: 1rem; }
            .pm-kpi-value { font-size: 1.7rem; }
            .pm-big { font-size: 1.9rem; }
            .pm-stats { grid-template-columns: 1fr; }
            .pm-card { margin-bottom: .75rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
