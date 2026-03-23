from __future__ import annotations

import streamlit as st


def inject_theme() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        :root {
            --bg: #0E1117;
            --panel: #151A23;
            --panel-2: #11161F;
            --border: rgba(255,255,255,0.08);
            --text: #E5E7EB;
            --muted: #94A3B8;
            --primary: #3B82F6;
            --positive: #22C55E;
            --negative: #EF4444;
            --warning: #F59E0B;
        }

        html, body, [class*="css"] {
            font-family: "Inter", sans-serif;
        }
        .stApp {
            background: var(--bg);
            color: var(--text);
        }
        [data-testid="stAppViewContainer"],
        [data-testid="stAppViewContainer"] .main,
        [data-testid="stAppViewContainer"] .main * {
            color: var(--text);
            font-family: "Inter", sans-serif !important;
        }
        [data-testid="stHeader"] {
            background: rgba(14,17,23,0.92);
            border-bottom: 1px solid var(--border);
        }
        [data-testid="stHeader"] *,
        [data-testid="stToolbar"] * {
            color: var(--muted) !important;
        }
        [data-testid="stSidebar"] {
            background: #0B0F15;
            border-right: 1px solid var(--border);
        }
        [data-testid="stSidebar"] * {
            color: var(--text) !important;
        }
        .pm-topbar {
            background: transparent;
            border: 0;
            box-shadow: none;
            padding: 0.1rem 0 0.6rem 0;
            margin-bottom: 1.2rem;
            color: var(--text);
        }
        .pm-brand {
            display: inline-flex;
            align-items: center;
            gap: .5rem;
            font-weight: 800;
            font-size: 1.7rem;
            color: #F8FAFC;
            letter-spacing: -0.03em;
        }
        .pm-shell,
        .pm-panel,
        .pm-summary,
        .pm-runrate,
        .pm-metric,
        details[data-testid="stExpander"] {
            background: var(--panel);
            border: 1px solid var(--border);
            box-shadow: none;
            border-radius: 18px;
        }
        .pm-shell {
            padding: 1rem 1.05rem;
            margin-bottom: 1.15rem;
        }
        .pm-panel {
            padding: 1.05rem 1.1rem;
        }
        .pm-summary {
            padding: 1.2rem 1.25rem;
        }
        .pm-runrate {
            padding: 1.2rem 1.25rem;
            border-color: rgba(59,130,246,0.24);
        }
        .pm-metric {
            min-height: 148px;
            padding: 1.1rem 1.15rem;
            position: relative;
            overflow: hidden;
        }
        .pm-metric::before {
            content: "";
            position: absolute;
            inset: 0 auto 0 0;
            width: 4px;
            background: var(--card-accent, var(--primary));
        }
        .pm-kicker {
            font-size: .70rem;
            text-transform: uppercase;
            letter-spacing: .14em;
            color: var(--muted);
            font-weight: 600;
        }
        .pm-value {
            font-size: 2.25rem;
            line-height: 1;
            font-weight: 800;
            letter-spacing: -0.04em;
            color: #F8FAFC;
            margin-top: .6rem;
        }
        .pm-label {
            font-size: .92rem;
            color: var(--muted);
            margin-top: .4rem;
            max-width: 18rem;
        }
        .pm-status {
            display: inline-flex;
            align-items: center;
            gap: .4rem;
            margin-top: .85rem;
            padding: .25rem .55rem;
            border-radius: 999px;
            font-size: .76rem;
            font-weight: 700;
            background: var(--status-bg, rgba(59,130,246,0.14));
            color: var(--status-fg, var(--primary));
        }
        .pm-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: currentColor;
        }
        [data-baseweb="tab-list"] {
            gap: .35rem;
            background: transparent;
            border: 0;
            padding: 0;
            margin-bottom: .75rem;
        }
        [data-baseweb="tab"] {
            background: transparent;
            border: 1px solid transparent;
            border-radius: 10px;
            padding: .5rem .85rem;
            color: var(--muted) !important;
            font-weight: 600;
            font-size: .92rem;
        }
        [aria-selected="true"][data-baseweb="tab"] {
            background: rgba(59,130,246,0.14);
            border-color: rgba(59,130,246,0.24);
            color: #EFF6FF !important;
        }
        h1, h2, h3, h4, h5, h6,
        .stMarkdown strong,
        .stMarkdown b {
            color: #F8FAFC !important;
            letter-spacing: -0.02em;
        }
        .stMarkdown p,
        .stCaption,
        p, li, span, label {
            color: var(--muted);
        }
        .stMarkdown code,
        .stCaption code,
        code {
            background: rgba(255,255,255,0.06) !important;
            color: #E2E8F0 !important;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 8px;
            padding: 0.12rem 0.38rem;
        }
        .stDataFrame, .stPlotlyChart {
            background: transparent;
            border-radius: 16px;
        }
        details[data-testid="stExpander"] {
            margin-bottom: 1rem;
        }
        details[data-testid="stExpander"] summary {
            color: #F8FAFC !important;
            font-weight: 700;
        }
        div[data-testid="stDataEditor"] {
            background: var(--panel-2);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: .35rem;
        }
        div[data-testid="stDataEditor"] * {
            color: var(--text) !important;
        }
        .stAlert {
            background: var(--panel);
            border: 1px solid var(--border);
        }
        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
