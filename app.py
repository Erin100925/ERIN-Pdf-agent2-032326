from __future__ import annotations

import os
import io
import re
import gc
import time
import json
import math
import uuid
import yaml
import base64
import hashlib
import datetime as dt
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Set

import streamlit as st

# Optional deps (handle gracefully)
try:
    import pandas as pd
except Exception:
    pd = None

try:
    from pydantic import BaseModel, Field, ValidationError
except Exception:
    BaseModel = object
    Field = lambda *a, **k: None
    ValidationError = Exception

try:
    from rapidfuzz import fuzz, process
except Exception:
    fuzz = None
    process = None

try:
    from PyPDF2 import PdfReader, PdfWriter
except Exception:
    PdfReader = None
    PdfWriter = None

try:
    from pdf2image import convert_from_bytes
except Exception:
    convert_from_bytes = None

try:
    import pytesseract
except Exception:
    pytesseract = None

try:
    import plotly.graph_objects as go
except Exception:
    go = None

# LLM provider SDKs (optional; will error with guidance if missing)
try:
    import google.generativeai as genai
except Exception:
    genai = None

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

try:
    import anthropic
except Exception:
    anthropic = None


# -----------------------------
# 0) App Metadata / Constants
# -----------------------------
APP_VERSION = "2.6"
APP_TITLE = f"FDA 510(k) Review Studio v{APP_VERSION} — Regulatory Command Center: WOW+"
TZ_NAME = "Asia/Taipei"

PROVIDERS = ["openai", "gemini", "anthropic", "grok"]

OPENAI_MODELS = ["gpt-4o-mini", "gpt-4.1-mini"]
GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3-flash-preview"]
# Anthropic model list is configurable; keep a safe default set (user can type custom)
ANTHROPIC_MODELS = ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest"]
GROK_MODELS = ["grok-4-fast-reasoning", "grok-3-mini"]

SUPPORTED_MODELS = {
    "openai": OPENAI_MODELS,
    "gemini": GEMINI_MODELS,
    "anthropic": ANTHROPIC_MODELS,
    "grok": GROK_MODELS,
}

DEFAULT_MAX_TOKENS = 12000
DEFAULT_TEMPERATURE = 0.2

RESERVED_CORAL = "#FF6F61"  # semantic critical highlight


# 20 painter-inspired palettes (simplified)
PAINTER_STYLES = {
    "van_gogh": {"name": "Van Gogh", "accent": "#F4D03F", "bg": "#0B1D3A", "panel": "#132A4C"},
    "monet": {"name": "Monet", "accent": "#76D7C4", "bg": "#0E2233", "panel": "#12334A"},
    "picasso": {"name": "Picasso", "accent": "#AF7AC5", "bg": "#1E1E2E", "panel": "#2A2A40"},
    "da_vinci": {"name": "Da Vinci", "accent": "#D4AC0D", "bg": "#1B1A17", "panel": "#2A2824"},
    "hokusai": {"name": "Hokusai", "accent": "#3498DB", "bg": "#071A2B", "panel": "#0B243B"},
    "kahlo": {"name": "Frida Kahlo", "accent": "#E74C3C", "bg": "#1C0F13", "panel": "#2B151B"},
    "matisse": {"name": "Matisse", "accent": "#F39C12", "bg": "#1B1226", "panel": "#271A3B"},
    "warhol": {"name": "Warhol", "accent": "#FF2D95", "bg": "#0C1020", "panel": "#111A33"},
    "turner": {"name": "Turner", "accent": "#F5B041", "bg": "#14110F", "panel": "#1F1A17"},
    "rembrandt": {"name": "Rembrandt", "accent": "#A04000", "bg": "#120C08", "panel": "#1B120D"},
    "klimt": {"name": "Klimt", "accent": "#D4AF37", "bg": "#0F0B06", "panel": "#1A140B"},
    "dali": {"name": "Dali", "accent": "#1ABC9C", "bg": "#081B1B", "panel": "#0D2A2A"},
    "pollock": {"name": "Pollock", "accent": "#E67E22", "bg": "#101114", "panel": "#171923"},
    "cezanne": {"name": "Cezanne", "accent": "#27AE60", "bg": "#0A1B12", "panel": "#0F2A1D"},
    "vermeer": {"name": "Vermeer", "accent": "#2E86C1", "bg": "#08162B", "panel": "#0C1F3C"},
    "goya": {"name": "Goya", "accent": "#922B21", "bg": "#0F0A0A", "panel": "#1B1010"},
    "cyberpunk": {"name": "Cyberpunk", "accent": "#00E5FF", "bg": "#080814", "panel": "#0E0E24"},
    "ukiyo_e": {"name": "Ukiyo-e", "accent": "#5DADE2", "bg": "#071623", "panel": "#0B2236"},
    "surreal": {"name": "Surreal", "accent": "#9B59B6", "bg": "#0C0714", "panel": "#140B24"},
    "minimal": {"name": "Minimal", "accent": "#95A5A6", "bg": "#0D0F10", "panel": "#141819"},
}

LANG = {
    "en": {
        "mode": "Mode",
        "command_center": "Command Center",
        "note_keeper": "AI Note Keeper",
        "theme": "Theme",
        "light": "Light",
        "dark": "Dark",
        "language": "Language",
        "painter_style": "Painter Style",
        "jackpot": "Jackpot",
        "api_keys": "API Keys",
        "managed_by_system": "Managed by System",
        "missing_key": "Missing",
        "session_key": "Session Key",
        "danger_zone": "Danger Zone",
        "total_purge": "Total Purge",
        "purge_confirm": "Purge everything in this session (docs, outputs, logs, keys).",
        "datasets": "Datasets",
        "search": "Search",
        "ingestion": "Ingestion",
        "upload_pdfs": "Upload PDFs",
        "paths": "File paths (optional)",
        "register_files": "Register Files",
        "queue": "File Queue",
        "trim": "Trim",
        "global_range": "Global page range",
        "execute_trim": "Execute Trim",
        "ocr": "OCR",
        "ocr_mode": "OCR Mode",
        "python_pack": "Python Pack (PyPDF2 + Tesseract)",
        "llm_ocr": "LLM OCR (Gemini multimodal)",
        "ocr_prompt": "OCR Prompt",
        "execute_ocr": "Execute OCR",
        "consolidated": "Consolidated OCR Markdown",
        "agent_orchestration": "Agent Orchestration",
        "agents_yaml": "agents.yaml",
        "validate_yaml": "Validate YAML",
        "run_agent": "Run Agent",
        "commit_next": "Commit as Next Input",
        "macro_summary": "Macro Summary",
        "persistent_prompt": "Persistent Prompt",
        "run_persistent_prompt": "Run Persistent Prompt",
        "dynamic_skill": "Dynamic Skill Execution",
        "skill_desc": "Skill Description",
        "run_skill": "Execute Skill on Summary",
        "wow_ai": "WOW AI",
        "evidence_mapper": "Evidence Mapper",
        "run_evidence": "Map Evidence",
        "consistency_guardian": "Consistency Guardian",
        "run_consistency": "Run Consistency Check",
        "risk_radar": "Regulatory Risk Radar",
        "run_risk": "Generate Risk Radar",
        "dashboards": "Dashboards",
        "mission_control": "Mission Control",
        "timeline": "Timeline / DAG",
        "logs": "Session Logs",
        "export": "Export",
        "low_resource": "Low-resource mode",
    },
    "zh-TW": {
        "mode": "模式",
        "command_center": "指揮中心",
        "note_keeper": "AI 筆記管家",
        "theme": "主題",
        "light": "亮色",
        "dark": "暗色",
        "language": "語言",
        "painter_style": "畫家風格",
        "jackpot": "隨機",
        "api_keys": "API 金鑰",
        "managed_by_system": "系統管理",
        "missing_key": "缺少",
        "session_key": "本次會話金鑰",
        "danger_zone": "危險區",
        "total_purge": "完全清除",
        "purge_confirm": "清除本次會話所有內容（文件、輸出、紀錄、金鑰）。",
        "datasets": "資料集",
        "search": "搜尋",
        "ingestion": "匯入",
        "upload_pdfs": "上傳 PDF",
        "paths": "檔案路徑（選用）",
        "register_files": "登錄檔案",
        "queue": "檔案佇列",
        "trim": "裁切",
        "global_range": "全域頁碼範圍",
        "execute_trim": "執行裁切",
        "ocr": "OCR",
        "ocr_mode": "OCR 模式",
        "python_pack": "Python 套件（PyPDF2 + Tesseract）",
        "llm_ocr": "LLM OCR（Gemini 多模態）",
        "ocr_prompt": "OCR 提示詞",
        "execute_ocr": "執行 OCR",
        "consolidated": "合併 OCR Markdown",
        "agent_orchestration": "代理人編排",
        "agents_yaml": "agents.yaml",
        "validate_yaml": "驗證 YAML",
        "run_agent": "執行代理人",
        "commit_next": "提交作為下一步輸入",
        "macro_summary": "巨集摘要",
        "persistent_prompt": "持續提示",
        "run_persistent_prompt": "執行持續提示",
        "dynamic_skill": "動態技能執行",
        "skill_desc": "技能描述",
        "run_skill": "對摘要執行技能",
        "wow_ai": "WOW AI",
        "evidence_mapper": "證據映射",
        "run_evidence": "映射證據",
        "consistency_guardian": "一致性守護",
        "run_consistency": "一致性檢查",
        "risk_radar": "法規風險雷達",
        "run_risk": "產生風險雷達",
        "dashboards": "儀表板",
        "mission_control": "任務控制台",
        "timeline": "時間線 / DAG",
        "logs": "會話紀錄",
        "export": "匯出",
        "low_resource": "低資源模式",
    },
}


# -----------------------------
# 1) Utilities
# -----------------------------
def now_taipei_str() -> str:
    # Lightweight timezone labeling; HF may not have pytz/zoneinfo consistently.
    # Use UTC+8 offset for Asia/Taipei.
    t = dt.datetime.utcnow() + dt.timedelta(hours=8)
    return t.strftime("%Y-%m-%d %H:%M:%S") + " (Asia/Taipei)"


def t(key: str) -> str:
    lang = st.session_state.get("ui.lang", "en")
    return LANG.get(lang, LANG["en"]).get(key, key)


def approx_tokens(text: str) -> int:
    # crude estimate ~4 chars/token
    if not text:
        return 0
    return max(1, len(text) // 4)


def sha256_hex(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def safe_event(component: str, severity: str, message: str, meta: Optional[dict] = None):
    if "obs.events" not in st.session_state:
        st.session_state["obs.events"] = []
    evt = {
        "ts": now_taipei_str(),
        "component": component,
        "severity": severity,
        "message": message,
        "meta": meta or {},
    }
    st.session_state["obs.events"].append(evt)


def set_pipeline_state(node: str, status: str, detail: str = ""):
    ps = st.session_state.setdefault("obs.pipeline_state", {})
    obj = ps.setdefault(node, {"status": "idle", "last_update": None, "detail": ""})
    obj["status"] = status
    obj["last_update"] = now_taipei_str()
    obj["detail"] = detail


def bump_metric(key: str, delta: float = 1.0):
    m = st.session_state.setdefault("obs.metrics", {})
    m[key] = m.get(key, 0.0) + delta


def mem_estimate_bytes() -> int:
    # rough: sum bytes for uploaded docs + trimmed + consolidated text lengths
    total = 0
    reg = st.session_state.get("docs.registry", [])
    for f in reg:
        b = f.get("bytes")
        if isinstance(b, (bytes, bytearray)):
            total += len(b)
    trim = st.session_state.get("docs.trim.outputs", {})
    for b in trim.values():
        if isinstance(b, (bytes, bytearray)):
            total += len(b)
    total += len(st.session_state.get("docs.consolidated_markdown", "") or "")
    return total


def human_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    for unit in ["KB", "MB", "GB", "TB"]:
        n /= 1024.0
        if n < 1024:
            return f"{n:.2f} {unit}"
    return f"{n:.2f} PB"


def parse_page_ranges(range_str: str) -> List[int]:
    """
    Accepts "1-5, 10, 15-20" and returns 0-based page indices.
    """
    if not range_str or not range_str.strip():
        return []
    parts = [p.strip() for p in range_str.split(",") if p.strip()]
    pages = set()
    for p in parts:
        if "-" in p:
            a, b = p.split("-", 1)
            a = int(a.strip())
            b = int(b.strip())
            if a <= 0 or b <= 0:
                raise ValueError("Page numbers must be >= 1.")
            if b < a:
                a, b = b, a
            for k in range(a, b + 1):
                pages.add(k - 1)
        else:
            k = int(p)
            if k <= 0:
                raise ValueError("Page numbers must be >= 1.")
            pages.add(k - 1)
    return sorted(pages)


def markdown_highlight_keywords(md: str, keywords_to_color: Dict[str, str]) -> str:
    # Simple HTML span injection for markdown rendering (best-effort).
    # Do NOT color reserved Coral terms via user palette; Coral is reserved for critical terms.
    if not md:
        return md
    # Apply user keywords first with longest-first to reduce overlap issues.
    items = sorted(keywords_to_color.items(), key=lambda kv: len(kv[0]), reverse=True)
    out = md
    for kw, color in items:
        if not kw:
            continue
        if color.strip().lower() == RESERVED_CORAL.lower():
            # reserved: skip user overriding coral
            continue
        pattern = re.compile(rf"(?i)\b({re.escape(kw)})\b")
        out = pattern.sub(rf"<span style='color:{color}; font-weight:700;'>\1</span>", out)
    # Baseline Coral highlights for critical ontology (minimal starter set)
    critical = ["warning", "recall", "latex", "implantable", "steril", "biocompat", "MDR", "adverse", "cybersecurity"]
    for kw in critical:
        pattern = re.compile(rf"(?i)\b({re.escape(kw)})\b")
        out = pattern.sub(rf"<span style='color:{RESERVED_CORAL}; font-weight:800;'>\1</span>", out)
    return out


# -----------------------------
# 2) Pydantic Models for agents.yaml
# -----------------------------
class AgentSpec(BaseModel):
    id: str
    name: str
    provider: str = Field(default="openai")
    model: str = Field(default="gpt-4o-mini")
    temperature: float = Field(default=DEFAULT_TEMPERATURE)
    max_tokens: int = Field(default=DEFAULT_MAX_TOKENS)
    system_prompt: str = Field(default="")
    user_prompt: str = Field(default="")
    expected_format: str = Field(default="markdown")


class AgentsConfig(BaseModel):
    agents: List[AgentSpec]


DEFAULT_AGENTS_YAML = """\
agents:
  - id: "a1"
    name: "Submission Structurer"
    provider: "openai"
    model: "gpt-4o-mini"
    temperature: 0.2
    max_tokens: 12000
    system_prompt: |
      You are a senior FDA 510(k) reviewer. Produce structured, factual analysis. Do not invent data.
      Output in Markdown with clear headings.
    user_prompt: |
      Convert the provided OCR text into a structured 510(k) review outline: Device Description, Indications for Use,
      Predicate Devices, Substantial Equivalence, Performance Testing, Biocompatibility, Sterilization/Shelf-life,
      Software/Cybersecurity (if relevant), Labeling, and Key Open Questions.
  - id: "a2"
    name: "Macro Summary (3000–4000 words)"
    provider: "openai"
    model: "gpt-4.1-mini"
    temperature: 0.2
    max_tokens: 12000
    system_prompt: |
      You are a regulatory writing engine. Be exhaustive, factual, and analytical.
      IMPORTANT: Target 3000 to 4000 words. Use Markdown. Include a clear Executive Summary and sectioned analysis.
    user_prompt: |
      Write a comprehensive 3000–4000 word FDA-style analytical review report based strictly on the provided content.
      Include a final section: "Reviewer Follow-up Questions".
"""


# -----------------------------
# 3) State Initialization / Migration
# -----------------------------
def init_state():
    ss = st.session_state

    # UI prefs
    ss.setdefault("ui.theme", "dark")
    ss.setdefault("ui.lang", "en")
    ss.setdefault("ui.painter_style", "cyberpunk")
    ss.setdefault("ui.jackpot_seed", 0)
    ss.setdefault("ui.preserve_prefs_on_purge", True)
    ss.setdefault("ui.low_resource_mode", False)

    # Keys
    ss.setdefault("keys.openai", None)
    ss.setdefault("keys.gemini", None)
    ss.setdefault("keys.anthropic", None)
    ss.setdefault("keys.grok", None)

    ss.setdefault("provider.health", {p: {"status": "unknown", "last_check": None, "last_error": ""} for p in PROVIDERS})

    # Data
    ss.setdefault("data.loaded", False)
    ss.setdefault("data.counts", {"510k": 0, "mdr": 0, "gudid": 0, "recall": 0})
    ss.setdefault("data.last_query", "")
    ss.setdefault("data.last_results", {})
    ss.setdefault("data.device_view", {})

    # Docs
    ss.setdefault("docs.registry", [])
    ss.setdefault("docs.queue.selected_ids", set())
    ss.setdefault("docs.trim.global_range", "1-5")
    ss.setdefault("docs.trim.per_file_override", {})
    ss.setdefault("docs.trim.outputs", {})
    ss.setdefault("docs.ocr.mode", "python_pack")
    ss.setdefault("docs.ocr.model", GEMINI_MODELS[0])
    ss.setdefault("docs.ocr.prompt", "Extract all text. Reconstruct tables in Markdown. Ignore headers/footers/watermarks.")
    ss.setdefault("docs.ocr.outputs_by_file", {})
    ss.setdefault("docs.consolidated_markdown", "")
    ss.setdefault("docs.consolidated_anchors", {})
    ss.setdefault("docs.preview.current", {"file_id": None, "page": None})

    # Artifacts
    ss.setdefault("artifacts", {})

    # Agents
    ss.setdefault("agents.yaml.raw", "")
    ss.setdefault("agents.yaml.validated", None)
    ss.setdefault("agents.run.order", [])
    ss.setdefault("agents.run.current_index", 0)
    ss.setdefault("agents.step.overrides", {})
    ss.setdefault("agents.step.input_source", {})
    ss.setdefault("agents.step.outputs", {})
    ss.setdefault("agents.timeline", {"nodes": [], "edges": []})
    ss.setdefault("agents.last_error", None)

    # Summary / skills
    ss.setdefault("summary.artifact_id", None)
    ss.setdefault("summary.persistent_prompt", "")
    ss.setdefault("skills.last_description", "")
    ss.setdefault("skills.outputs", [])

    # Note keeper
    ss.setdefault("notes.input_raw", "")
    ss.setdefault("notes.output_artifact_id", None)
    ss.setdefault("notes.model_provider", "openai")
    ss.setdefault("notes.model", "gpt-4o-mini")
    ss.setdefault("notes.prompt", "Organize the note into clean Markdown with headings, bullets, and action items.")
    ss.setdefault("notes.keywords.palette", {"FDA": "#7FB3D5", "biocompatibility": "#82E0AA"})
    ss.setdefault("notes.magics.history", [])

    # Observability
    ss.setdefault("obs.events", [])
    ss.setdefault("obs.metrics", {})
    ss.setdefault("obs.pipeline_state", {})
    ss.setdefault("obs.export.ready", {})

    # Mode
    ss.setdefault("ui.mode", "command_center")


def total_purge():
    preserve = st.session_state.get("ui.preserve_prefs_on_purge", True)
    theme = st.session_state.get("ui.theme")
    lang = st.session_state.get("ui.lang")
    painter = st.session_state.get("ui.painter_style")
    seed = st.session_state.get("ui.jackpot_seed")
    low_resource = st.session_state.get("ui.low_resource_mode", False)

    st.session_state.clear()
    init_state()

    if preserve:
        st.session_state["ui.theme"] = theme
        st.session_state["ui.lang"] = lang
        st.session_state["ui.painter_style"] = painter
        st.session_state["ui.jackpot_seed"] = seed
        st.session_state["ui.low_resource_mode"] = low_resource

    safe_event("danger_zone", "warn", "Total purge executed.")
    gc.collect()


# -----------------------------
# 4) Theming / CSS
# -----------------------------
def inject_css():
    style_id = st.session_state.get("ui.painter_style", "cyberpunk")
    palette = PAINTER_STYLES.get(style_id, PAINTER_STYLES["cyberpunk"])
    theme = st.session_state.get("ui.theme", "dark")
    accent = palette["accent"]
    bg = palette["bg"]
    panel = palette["panel"]

    if theme == "light":
        # shift to lighter background while keeping accent
        bg = "#F6F7FB"
        panel = "rgba(255,255,255,0.72)"

    css = f"""
    <style>
      .stApp {{
        background: radial-gradient(circle at 10% 10%, rgba(255,255,255,0.04), transparent 40%),
                    radial-gradient(circle at 90% 20%, rgba(255,255,255,0.03), transparent 35%),
                    {bg};
        color: {"#0B0E14" if theme=="light" else "#EAF0FF"};
      }}

      /* Glass panels */
      .wow-panel {{
        background: {panel};
        border: 1px solid rgba(255,255,255,0.14);
        border-radius: 16px;
        padding: 14px 14px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.25);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
      }}

      /* Accent buttons */
      div.stButton > button {{
        border-radius: 12px !important;
        border: 1px solid rgba(255,255,255,0.18) !important;
        background: linear-gradient(135deg, rgba(255,255,255,0.10), rgba(255,255,255,0.04)) !important;
        color: inherit !important;
      }}
      div.stButton > button:hover {{
        border-color: {accent} !important;
        box-shadow: 0 0 0 3px rgba(0,0,0,0.0), 0 0 18px rgba(0,0,0,0.0), 0 0 14px {accent}55;
      }}

      /* Accent for sliders/select */
      .wow-accent {{
        color: {accent};
        font-weight: 700;
      }}

      /* Coral reserved highlight */
      .wow-coral {{
        color: {RESERVED_CORAL};
        font-weight: 800;
      }}

      /* Status chips */
      .wow-chip {{
        display:inline-block;
        padding: 6px 10px;
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,0.16);
        background: rgba(255,255,255,0.06);
        margin-right: 8px;
        margin-bottom: 8px;
        font-size: 12px;
      }}
      .wow-chip.ok {{ border-color: rgba(46, 204, 113, 0.55); }}
      .wow-chip.warn {{ border-color: rgba(241, 196, 15, 0.55); }}
      .wow-chip.err {{ border-color: rgba(231, 76, 60, 0.55); }}

      /* Make markdown tables nicer */
      .stMarkdown table {{
        border-collapse: collapse;
        width: 100%;
      }}
      .stMarkdown th, .stMarkdown td {{
        border: 1px solid rgba(255,255,255,0.18);
        padding: 6px 8px;
      }}
      .stMarkdown th {{
        background: rgba(255,255,255,0.07);
      }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


# -----------------------------
# 5) Datasets (cached load)
# -----------------------------
@st.cache_data(show_spinner=False)
def load_dataset_csv(path: str) -> "pd.DataFrame":
    if pd is None:
        raise RuntimeError("pandas is not installed.")
    return pd.read_csv(path)


def load_datasets_best_effort():
    """
    Attempt to load datasets from local files. If not present, create empty placeholders.
    Expected files (customize to your repo structure):
      data/510k.csv, data/mdr.csv, data/gudid.csv, data/recall.csv
    """
    if pd is None:
        safe_event("data", "warn", "pandas not installed; dataset features disabled.")
        st.session_state["data.loaded"] = False
        return

    base = "data"
    files = {
        "510k": os.path.join(base, "510k.csv"),
        "mdr": os.path.join(base, "mdr.csv"),
        "gudid": os.path.join(base, "gudid.csv"),
        "recall": os.path.join(base, "recall.csv"),
    }
    dfs = {}
    counts = {}
    for k, fp in files.items():
        if os.path.exists(fp):
            try:
                df = load_dataset_csv(fp)
                dfs[k] = df
                counts[k] = int(len(df))
                safe_event("data", "info", f"Loaded dataset {k} ({counts[k]} rows).")
            except Exception as e:
                dfs[k] = pd.DataFrame()
                counts[k] = 0
                safe_event("data", "err", f"Failed loading dataset {k}: {e}")
        else:
            dfs[k] = pd.DataFrame()
            counts[k] = 0

    st.session_state["dataframes"] = dfs
    st.session_state["data.counts"] = counts
    st.session_state["data.loaded"] = True


def fuzzy_search_all(query: str, limit: int = 25) -> Dict[str, Any]:
    """
    Best-effort fuzzy search across the four datasets.
    Uses rapidfuzz if available; otherwise simple contains filtering.
    """
    dfs = st.session_state.get("dataframes", {})
    results = {}
    if not query.strip():
        return results

    for name, df in dfs.items():
        if df is None or getattr(df, "empty", True):
            results[name] = None
            continue

        # Choose candidate columns
        cols = [c for c in df.columns if any(s in c.lower() for s in ["device", "name", "applicant", "k_number", "product", "code", "manufacturer", "udi"])]
        cols = cols[:6] if cols else list(df.columns[:4])

        try:
            if fuzz and process:
                # Create a searchable series
                comb = df[cols].astype(str).fillna("").agg(" | ".join, axis=1).tolist()
                matches = process.extract(query, comb, scorer=fuzz.partial_ratio, limit=min(limit, len(comb)))
                idxs = [m[2] for m in matches if m[1] >= 60]  # threshold
                sub = df.iloc[idxs].copy()
                sub["_score"] = [m[1] for m in matches if m[1] >= 60]
                results[name] = sub
            else:
                mask = None
                for c in cols:
                    m = df[c].astype(str).str.contains(query, case=False, na=False)
                    mask = m if mask is None else (mask | m)
                sub = df[mask].head(limit).copy()
                results[name] = sub
        except Exception as e:
            safe_event("search", "err", f"Search failed for {name}: {e}")
            results[name] = None

    return results


# -----------------------------
# 6) Artifacts / Versioning
# -----------------------------
def create_artifact(initial_text: str, fmt: str, metadata: Optional[dict] = None) -> str:
    artifacts = st.session_state["artifacts"]
    artifact_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())
    artifacts[artifact_id] = {
        "current_version_id": version_id,
        "versions": [
            {
                "version_id": version_id,
                "created_at": now_taipei_str(),
                "created_by": "system",
                "content_text": initial_text or "",
                "content_format": fmt,
                "metadata": metadata or {},
                "parent_version_id": None,
            }
        ],
    }
    return artifact_id


def artifact_get_current(artifact_id: str) -> Tuple[str, dict]:
    artifacts = st.session_state["artifacts"]
    a = artifacts.get(artifact_id)
    if not a:
        return "", {}
    cur = a["current_version_id"]
    for v in reversed(a["versions"]):
        if v["version_id"] == cur:
            return v["content_text"], v
    # fallback
    v = a["versions"][-1]
    return v["content_text"], v


def artifact_add_version(artifact_id: str, new_text: str, created_by: str, metadata: Optional[dict] = None, parent_version_id: Optional[str] = None) -> str:
    artifacts = st.session_state["artifacts"]
    a = artifacts.get(artifact_id)
    if not a:
        raise KeyError("artifact not found")
    version_id = str(uuid.uuid4())
    a["versions"].append(
        {
            "version_id": version_id,
            "created_at": now_taipei_str(),
            "created_by": created_by,
            "content_text": new_text or "",
            "content_format": "markdown",
            "metadata": metadata or {},
            "parent_version_id": parent_version_id or a.get("current_version_id"),
        }
    )
    a["current_version_id"] = version_id
    return version_id


def artifact_versions(artifact_id: str) -> List[dict]:
    artifacts = st.session_state["artifacts"]
    a = artifacts.get(artifact_id, {})
    return a.get("versions", [])


def simple_diff(a: str, b: str, max_lines: int = 200) -> str:
    """
    Lightweight line diff (no external deps).
    """
    import difflib

    a_lines = (a or "").splitlines()
    b_lines = (b or "").splitlines()
    diff = difflib.unified_diff(a_lines, b_lines, lineterm="", fromfile="prev", tofile="current")
    out = "\n".join(list(diff)[:max_lines])
    if len(out) == 0:
        out = "(no diff)"
    return "```diff\n" + out + "\n```"


# -----------------------------
# 7) agents.yaml load/validate
# -----------------------------
def load_agents_yaml():
    if st.session_state.get("agents.yaml.raw"):
        return

    raw = ""
    if os.path.exists("agents.yaml"):
        try:
            with open("agents.yaml", "r", encoding="utf-8") as f:
                raw = f.read()
        except Exception as e:
            safe_event("agents", "err", f"Failed reading agents.yaml: {e}")

    st.session_state["agents.yaml.raw"] = raw.strip() or DEFAULT_AGENTS_YAML


def validate_agents_yaml(raw: str) -> Optional[AgentsConfig]:
    try:
        parsed = yaml.safe_load(raw) or {}
        cfg = AgentsConfig(**parsed)
        # basic provider checks
        for a in cfg.agents:
            if a.provider not in PROVIDERS:
                raise ValueError(f"Unsupported provider: {a.provider} in agent {a.id}")
        return cfg
    except Exception as e:
        st.session_state["agents.last_error"] = str(e)
        return None


# -----------------------------
# 8) Document ingestion / trim / OCR
# -----------------------------
def register_uploaded_files(uploaded_files: list):
    if not uploaded_files:
        return

    reg = st.session_state["docs.registry"]
    existing_names = {f["name"] for f in reg}

    for uf in uploaded_files:
        try:
            b = uf.read()
            file_id = str(uuid.uuid4())
            if uf.name in existing_names:
                uf_name = f"{uf.name} ({file_id[:8]})"
            else:
                uf_name = uf.name

            reg.append(
                {
                    "id": file_id,
                    "name": uf_name,
                    "source": "upload",
                    "bytes": b,
                    "path": None,
                    "size": len(b),
                    "page_count": None,
                    "health": "unknown",
                    "created_at": now_taipei_str(),
                }
            )
            safe_event("ingestion", "info", f"Registered upload: {uf_name} ({human_size(len(b))}).")
        except Exception as e:
            safe_event("ingestion", "err", f"Failed registering upload {getattr(uf, 'name', 'file')}: {e}")

    set_pipeline_state("ingestion", "done", f"Registry size: {len(st.session_state['docs.registry'])}")


def register_file_paths(paths_text: str):
    if not paths_text.strip():
        return
    reg = st.session_state["docs.registry"]
    lines = [ln.strip() for ln in paths_text.splitlines() if ln.strip()]
    for p in lines:
        try:
            if not os.path.exists(p):
                safe_event("ingestion", "warn", f"Path not found: {p}")
                continue
            if not p.lower().endswith(".pdf"):
                safe_event("ingestion", "warn", f"Not a PDF: {p}")
                continue
            with open(p, "rb") as f:
                b = f.read()
            file_id = str(uuid.uuid4())
            name = os.path.basename(p)
            reg.append(
                {
                    "id": file_id,
                    "name": name,
                    "source": "path",
                    "bytes": b,
                    "path": p,
                    "size": len(b),
                    "page_count": None,
                    "health": "unknown",
                    "created_at": now_taipei_str(),
                }
            )
            safe_event("ingestion", "info", f"Registered path: {name} ({human_size(len(b))}).")
        except Exception as e:
            safe_event("ingestion", "err", f"Failed reading path {p}: {e}")

    set_pipeline_state("ingestion", "done", f"Registry size: {len(st.session_state['docs.registry'])}")


def scan_pdf_metadata(file_obj: dict):
    if PdfReader is None:
        file_obj["health"] = "no_pypdf2"
        return
    try:
        reader = PdfReader(io.BytesIO(file_obj["bytes"]))
        file_obj["page_count"] = len(reader.pages)
        file_obj["health"] = "ok"
    except Exception as e:
        file_obj["health"] = f"error: {e}"


def ensure_scanned_metadata():
    for f in st.session_state["docs.registry"]:
        if f.get("page_count") is None and isinstance(f.get("bytes"), (bytes, bytearray)):
            scan_pdf_metadata(f)


def trim_pdf_bytes(pdf_bytes: bytes, page_indices: List[int]) -> bytes:
    if PdfReader is None or PdfWriter is None:
        raise RuntimeError("PyPDF2 is not available.")
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    max_page = len(reader.pages) - 1
    for idx in page_indices:
        if idx < 0:
            continue
        if idx > max_page:
            continue
        writer.add_page(reader.pages[idx])
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def execute_trimming(policy_out_of_range: str = "clip_with_warn"):
    set_pipeline_state("trim", "running", "Trimming selected PDFs...")
    reg = st.session_state["docs.registry"]
    selected: Set[str] = st.session_state["docs.queue.selected_ids"] or set()
    global_range = st.session_state.get("docs.trim.global_range", "1-5")
    per_override = st.session_state.get("docs.trim.per_file_override", {})

    outputs = {}
    warnings = 0

    for f in reg:
        if f["id"] not in selected:
            continue
        rng = per_override.get(f["id"], "").strip() or global_range
        try:
            indices = parse_page_ranges(rng)
            if f.get("page_count") is not None and indices:
                max_page = f["page_count"] - 1
                if indices[-1] > max_page:
                    if policy_out_of_range == "block":
                        raise ValueError(f"Range exceeds page count ({f['page_count']}).")
                    if policy_out_of_range == "skip_file":
                        safe_event("trim", "warn", f"Skipping {f['name']}: range exceeds page count.")
                        warnings += 1
                        continue
                    # clip_with_warn
                    indices = [i for i in indices if i <= max_page]
                    safe_event("trim", "warn", f"Clipped range for {f['name']} to max page {f['page_count']}.")

            outputs[f["id"]] = trim_pdf_bytes(f["bytes"], indices)
            safe_event("trim", "info", f"Trimmed {f['name']} with range '{rng}' -> {human_size(len(outputs[f['id']]))}.")
        except Exception as e:
            safe_event("trim", "err", f"Trimming failed for {f['name']}: {e}")
            warnings += 1

    st.session_state["docs.trim.outputs"] = outputs
    set_pipeline_state("trim", "done" if warnings == 0 else "warn", f"Trimmed files: {len(outputs)}")
    bump_metric("trim.files", len(outputs))


def ocr_python_pack(pdf_bytes: bytes, low_resource: bool = False) -> str:
    """
    Best-effort:
      1) PyPDF2 extract_text
      2) If empty and pdf2image+pytesseract available: render first few pages and OCR
    """
    text = ""
    if PdfReader is not None:
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            chunks = []
            for i, p in enumerate(reader.pages):
                try:
                    chunks.append(p.extract_text() or "")
                except Exception:
                    chunks.append("")
                # low-resource: stop early
                if low_resource and i >= 4:
                    break
            text = "\n".join(chunks).strip()
        except Exception as e:
            safe_event("ocr", "warn", f"PyPDF2 extraction failed: {e}")

    if text:
        return text

    # fallback OCR
    if convert_from_bytes is None or pytesseract is None:
        safe_event("ocr", "warn", "Tesseract/pdf2image not available; returning empty text.")
        return ""

    images = convert_from_bytes(pdf_bytes, dpi=200 if low_resource else 300)
    out_chunks = []
    for idx, img in enumerate(images):
        try:
            out_chunks.append(pytesseract.image_to_string(img))
        except Exception as e:
            safe_event("ocr", "warn", f"Tesseract OCR failed page {idx+1}: {e}")
        if low_resource and idx >= 4:
            break
    return "\n".join(out_chunks).strip()


def gemini_llm_ocr(pdf_bytes: bytes, model: str, prompt: str, low_resource: bool = False) -> str:
    if genai is None:
        raise RuntimeError("google-generativeai is not installed.")
    api_key = get_effective_key("gemini")
    if not api_key:
        raise RuntimeError("Gemini API key missing.")
    genai.configure(api_key=api_key)

    # Render pdf -> images
    if convert_from_bytes is None:
        raise RuntimeError("pdf2image not installed; cannot render images for LLM OCR.")

    images = convert_from_bytes(pdf_bytes, dpi=180 if low_resource else 300)
    # Low-resource: limit pages aggressively
    if low_resource:
        images = images[:5]

    # Gemini expects parts; we'll send per page and concatenate for stability
    # (reduces payload sizes and supports incremental progress)
    out = []
    mdl = genai.GenerativeModel(model)

    for i, img in enumerate(images, start=1):
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b = buf.getvalue()
        parts = [
            {"text": prompt},
            {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(b).decode("utf-8")}},
        ]
        try:
            resp = mdl.generate_content(parts)
            out_text = getattr(resp, "text", "") or ""
            out.append(out_text.strip())
            safe_event("ocr", "info", f"Gemini OCR page {i}/{len(images)} done.", {"model": model})
            bump_metric("gemini.calls", 1)
        except Exception as e:
            safe_event("ocr", "err", f"Gemini OCR failed page {i}: {e}", {"model": model})
            bump_metric("gemini.errors", 1)
            out.append(f"\n\n[OCR ERROR page {i}: {e}]\n\n")

    return "\n\n".join(out).strip()


def assemble_consolidated_markdown(outputs_by_file: Dict[str, str]) -> Tuple[str, Dict[str, dict]]:
    """
    Creates a single Markdown artifact with stable anchors.
    Anchor lines: --- ANCHOR: {anchor_id} | FILE: ... | PAGE: {n} ---
    Note: For python pack extraction we don't have per-page boundaries; still generate a per-file anchor.
    """
    anchors = {}
    reg = {f["id"]: f for f in st.session_state["docs.registry"]}
    pieces = []
    for file_id, content in outputs_by_file.items():
        f = reg.get(file_id, {"name": file_id})
        # If OCR was per-page concatenation, we can't reliably split; treat as one anchor.
        anchor_id = f"anc_{file_id[:8]}_p1"
        anchors[anchor_id] = {"file_id": file_id, "file_name": f.get("name"), "page": 1}
        header = f"--- ANCHOR: {anchor_id} | FILE: {f.get('name')} | PAGE: 1 ---"
        pieces.append(header)
        pieces.append(content or "")
        pieces.append("\n\n")
    return "\n".join(pieces).strip(), anchors


def execute_ocr():
    set_pipeline_state("ocr", "running", "OCR running...")
    selected: Set[str] = st.session_state["docs.queue.selected_ids"] or set()
    trimmed = st.session_state.get("docs.trim.outputs", {})
    mode = st.session_state.get("docs.ocr.mode", "python_pack")
    low_resource = st.session_state.get("ui.low_resource_mode", False)

    outputs = {}
    total = 0
    for file_id, pdf_bytes in trimmed.items():
        if file_id not in selected:
            continue
        total += 1

    done = 0
    progress = st.progress(0.0)
    for file_id, pdf_bytes in trimmed.items():
        if file_id not in selected:
            continue
        done += 1
        progress.progress(done / max(1, total))
        name = next((f["name"] for f in st.session_state["docs.registry"] if f["id"] == file_id), file_id)
        try:
            if mode == "python_pack":
                text = ocr_python_pack(pdf_bytes, low_resource=low_resource)
                outputs[file_id] = text
                safe_event("ocr", "info", f"Python OCR done: {name}")
                bump_metric("ocr.python.files", 1)
            else:
                model = st.session_state.get("docs.ocr.model", GEMINI_MODELS[0])
                prompt = st.session_state.get("docs.ocr.prompt", "")
                md = gemini_llm_ocr(pdf_bytes, model=model, prompt=prompt, low_resource=low_resource)
                outputs[file_id] = md
                bump_metric("ocr.gemini.files", 1)
        except Exception as e:
            safe_event("ocr", "err", f"OCR failed for {name}: {e}")
            outputs[file_id] = f"\n\n[OCR ERROR for {name}: {e}]\n\n"
            bump_metric("ocr.errors", 1)

    st.session_state["docs.ocr.outputs_by_file"] = outputs
    consolidated, anchors = assemble_consolidated_markdown(outputs)
    st.session_state["docs.consolidated_markdown"] = consolidated
    st.session_state["docs.consolidated_anchors"] = anchors

    # Create/overwrite consolidated artifact
    if not st.session_state.get("consolidated.artifact_id"):
        aid = create_artifact(consolidated, fmt="markdown", metadata={"source": "ocr_consolidation"})
        st.session_state["consolidated.artifact_id"] = aid
    else:
        aid = st.session_state["consolidated.artifact_id"]
        artifact_add_version(aid, consolidated, created_by="ocr", metadata={"source": "ocr_consolidation"})

    set_pipeline_state("ocr", "done", f"OCR files: {len(outputs)}")
    set_pipeline_state("consolidation", "done", f"Chars: {len(consolidated)}")
    bump_metric("ocr.files", len(outputs))


# -----------------------------
# 9) Provider key management + LLM execution
# -----------------------------
def get_env_key(provider: str) -> Optional[str]:
    if provider == "openai":
        return os.getenv("OPENAI_API_KEY")
    if provider == "gemini":
        return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_GENERATIVEAI_API_KEY")
    if provider == "anthropic":
        return os.getenv("ANTHROPIC_API_KEY")
    if provider == "grok":
        return os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY")
    return None


def get_effective_key(provider: str) -> Optional[str]:
    env = get_env_key(provider)
    if env:
        return env
    return st.session_state.get(f"keys.{provider}")


def provider_key_source(provider: str) -> str:
    if get_env_key(provider):
        return "env"
    if st.session_state.get(f"keys.{provider}"):
        return "session"
    return "missing"


def render_key_section():
    st.sidebar.markdown(f"### {t('api_keys')}")
    for p in PROVIDERS:
        src = provider_key_source(p)
        label = f"{p.upper()} — " + (t("managed_by_system") if src == "env" else (t("session_key") if src == "session" else t("missing_key")))
        if src == "env":
            st.sidebar.success(label)
        elif src == "session":
            st.sidebar.warning(label)
        else:
            st.sidebar.error(label)

        # Only show input if missing in env
        if src != "env":
            st.sidebar.text_input(
                f"{p.upper()} API Key",
                type="password",
                value=st.session_state.get(f"keys.{p}") or "",
                key=f"keys.{p}",
                help="Stored only in this session state. Not logged. Cleared by Total Purge.",
            )


def llm_execute(provider: str, model: str, system_prompt: str, user_prompt: str, context: str,
                max_tokens: int, temperature: float, expect_markdown: bool = True) -> Tuple[str, dict]:
    """
    Provider-agnostic execute for TEXT tasks (agents, notes, skills).
    """
    start = time.time()
    safe_event("llm", "info", f"LLM execute start: {provider}/{model}", {"max_tokens": max_tokens})

    key = get_effective_key(provider)
    if not key:
        raise RuntimeError(f"Missing API key for provider: {provider}")

    # Basic payload
    full_user = (user_prompt or "").strip()
    if context:
        full_user = full_user + "\n\n--- CONTEXT START ---\n" + context + "\n--- CONTEXT END ---\n"

    # Execute
    content = ""
    usage = {"input_tokens_est": approx_tokens(system_prompt + full_user), "output_tokens_est": None}

    if provider == "openai":
        if OpenAI is None:
            raise RuntimeError("openai SDK not installed.")
        client = OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt or ""},
                {"role": "user", "content": full_user},
            ],
            max_tokens=int(max_tokens),
            temperature=float(temperature),
        )
        content = resp.choices[0].message.content or ""
        try:
            usage["usage"] = {
                "prompt_tokens": getattr(resp.usage, "prompt_tokens", None),
                "completion_tokens": getattr(resp.usage, "completion_tokens", None),
                "total_tokens": getattr(resp.usage, "total_tokens", None),
            }
        except Exception:
            pass

    elif provider == "grok":
        # Grok is commonly OpenAI-compatible; allow custom base_url.
        if OpenAI is None:
            raise RuntimeError("openai SDK not installed (needed for OpenAI-compatible endpoints).")
        base_url = os.getenv("GROK_BASE_URL") or os.getenv("XAI_BASE_URL") or "https://api.x.ai/v1"
        client = OpenAI(api_key=key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt or ""},
                {"role": "user", "content": full_user},
            ],
            max_tokens=int(max_tokens),
            temperature=float(temperature),
        )
        content = resp.choices[0].message.content or ""

    elif provider == "anthropic":
        if anthropic is None:
            raise RuntimeError("anthropic SDK not installed.")
        client = anthropic.Anthropic(api_key=key)
        # Anthropic separates system prompt:
        resp = client.messages.create(
            model=model,
            max_tokens=int(max_tokens),
            temperature=float(temperature),
            system=system_prompt or "",
            messages=[{"role": "user", "content": full_user}],
        )
        # resp.content is list of blocks
        parts = []
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                parts.append(block.text)
        content = "\n".join(parts).strip()

    elif provider == "gemini":
        if genai is None:
            raise RuntimeError("google-generativeai SDK not installed.")
        genai.configure(api_key=key)
        mdl = genai.GenerativeModel(model)
        # Gemini does not have strict system prompt in same way; prepend into user text
        msg = ""
        if system_prompt:
            msg += f"[SYSTEM]\n{system_prompt}\n\n"
        msg += full_user
        resp = mdl.generate_content(msg)
        content = getattr(resp, "text", "") or ""

    else:
        raise RuntimeError(f"Unsupported provider: {provider}")

    elapsed = int((time.time() - start) * 1000)
    bump_metric(f"{provider}.calls", 1)
    bump_metric(f"{provider}.latency_ms_total", elapsed)
    safe_event("llm", "info", f"LLM execute done: {provider}/{model} ({elapsed}ms)")
    return content, {"latency_ms": elapsed, "usage": usage, "provider": provider, "model": model}


# -----------------------------
# 10) Agent Orchestration helpers
# -----------------------------
def timeline_add_node(kind: str, title: str, artifact_id: Optional[str], meta: dict) -> str:
    node_id = str(uuid.uuid4())
    tl = st.session_state["agents.timeline"]
    tl["nodes"].append(
        {"node_id": node_id, "kind": kind, "title": title, "artifact_id": artifact_id, "ts": now_taipei_str(), "meta": meta}
    )
    return node_id


def timeline_add_edge(src_node_id: str, dst_node_id: str, label: str = "handoff"):
    tl = st.session_state["agents.timeline"]
    tl["edges"].append({"src": src_node_id, "dst": dst_node_id, "label": label, "ts": now_taipei_str()})


def run_agent(agent: AgentSpec, context: str, overrides: dict) -> Tuple[str, dict]:
    provider = overrides.get("provider", agent.provider)
    model = overrides.get("model", agent.model)
    max_tokens = int(overrides.get("max_tokens", agent.max_tokens or DEFAULT_MAX_TOKENS))
    temperature = float(overrides.get("temperature", agent.temperature if agent.temperature is not None else DEFAULT_TEMPERATURE))
    system_prompt = overrides.get("system_prompt", agent.system_prompt or "")
    user_prompt = overrides.get("user_prompt", agent.user_prompt or "")

    out, meta = llm_execute(
        provider=provider,
        model=model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        context=context,
        max_tokens=max_tokens,
        temperature=temperature,
        expect_markdown=True,
    )
    meta["prompts_hash"] = {
        "system": sha256_hex(system_prompt),
        "user": sha256_hex(user_prompt),
        "context": sha256_hex(context[:5000] if context else ""),
    }
    meta["max_tokens"] = max_tokens
    meta["temperature"] = temperature
    return out, meta


# -----------------------------
# 11) WOW AI Features (heuristic-first, optional LLM later)
# -----------------------------
def extract_claims(text: str, max_claims: int = 80) -> List[str]:
    """
    Simple claim extraction: bullet lines + longer sentences with numbers.
    """
    if not text:
        return []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    claims = []
    for ln in lines:
        if ln.startswith(("-", "*", "•")) and len(ln) > 25:
            claims.append(ln.lstrip("-*• ").strip())
    # sentence-based
    sents = re.split(r"(?<=[\.\?!])\s+", text)
    for s in sents:
        s = s.strip()
        if len(s) < 40:
            continue
        if re.search(r"\d", s) or any(k in s.lower() for k in ["shall", "must", "demonstrat", "tested", "complied", "indicat"]):
            claims.append(s)
    # dedupe
    uniq = []
    seen = set()
    for c in claims:
        key = c.lower()[:180]
        if key not in seen:
            uniq.append(c)
            seen.add(key)
        if len(uniq) >= max_claims:
            break
    return uniq


def build_anchor_index(consolidated_md: str) -> List[Tuple[int, str]]:
    """
    Returns list of (pos, anchor_id) where pos is char index in consolidated_md.
    """
    idx = []
    for m in re.finditer(r"---\s*ANCHOR:\s*([A-Za-z0-9_\-]+)\s*\|", consolidated_md or ""):
        idx.append((m.start(), m.group(1)))
    idx.sort(key=lambda x: x[0])
    return idx


def find_nearest_anchor(anchor_index: List[Tuple[int, str]], position: int) -> Optional[str]:
    if not anchor_index:
        return None
    # find rightmost anchor whose pos <= position
    lo, hi = 0, len(anchor_index) - 1
    best = None
    while lo <= hi:
        mid = (lo + hi) // 2
        pos, aid = anchor_index[mid]
        if pos <= position:
            best = aid
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def evidence_mapper_run(target_text: str) -> Tuple[str, List[dict]]:
    consolidated = st.session_state.get("docs.consolidated_markdown", "") or ""
    anchors = st.session_state.get("docs.consolidated_anchors", {}) or {}
    if not consolidated.strip():
        raise RuntimeError("No consolidated OCR text available.")

    anchor_index = build_anchor_index(consolidated)
    claims = extract_claims(target_text, max_claims=60)
    if not claims:
        return "No claims detected.", []

    # Create searchable chunks: lines with positions
    lines = consolidated.splitlines()
    positions = []
    cur = 0
    for ln in lines:
        positions.append(cur)
        cur += len(ln) + 1

    # For matching: combine lines into a corpus
    corpus = lines
    results = []
    for c in claims:
        best = {"score": 0, "line": "", "pos": None}
        # rapidfuzz preferred
        if fuzz is not None:
            for i, ln in enumerate(corpus):
                if not ln.strip():
                    continue
                s = fuzz.partial_ratio(c[:300], ln[:400])
                if s > best["score"]:
                    best = {"score": s, "line": ln, "pos": positions[i]}
        else:
            # fallback contains
            for i, ln in enumerate(corpus):
                if c[:40].lower() in ln.lower():
                    best = {"score": 70, "line": ln, "pos": positions[i]}
                    break

        anchor_id = find_nearest_anchor(anchor_index, best["pos"] or 0) if best["pos"] is not None else None
        anc_meta = anchors.get(anchor_id, {}) if anchor_id else {}

        results.append(
            {
                "claim": c,
                "confidence": best["score"],
                "evidence_quote": best["line"][:500] if best["line"] else "",
                "anchor_id": anchor_id or "",
                "file": anc_meta.get("file_name", ""),
                "page": anc_meta.get("page", ""),
            }
        )

    # Build Markdown table
    md_lines = [
        "## Evidence Map",
        "",
        f"- Claims analyzed: **{len(results)}**",
        f"- Coverage (has anchor): **{sum(1 for r in results if r['anchor_id'])}/{len(results)}**",
        "",
        "| Claim | Confidence | Evidence Quote | Anchor | File | Page |",
        "|---|---:|---|---|---|---:|",
    ]
    for r in results:
        claim = (r["claim"][:160] + "…") if len(r["claim"]) > 160 else r["claim"]
        quote = (r["evidence_quote"][:140] + "…") if len(r["evidence_quote"]) > 140 else r["evidence_quote"]
        md_lines.append(
            f"| {claim.replace('|','\\|')} | {r['confidence']} | {quote.replace('|','\\|')} | {r['anchor_id']} | {r['file']} | {r['page']} |"
        )
    md = "\n".join(md_lines)
    return md, results


def consistency_guardian_run(summary_text: str) -> str:
    """
    Heuristic checks for:
      - missing required sections
      - conflicting values for shelf life / sterilization / indications / product code
    """
    issues = []
    text = summary_text or ""
    lower = text.lower()

    required_headings = [
        "device description",
        "indications",
        "predicate",
        "performance",
        "biocompat",
        "steril",
        "label",
    ]
    missing = [h for h in required_headings if h not in lower]
    for h in missing:
        issues.append({"severity": "high", "title": "Missing section", "detail": f"Required section not found: '{h}'"})

    # conflicting numeric shelf life
    shelf = re.findall(r"(shelf\s*life[^.\n]{0,80})", lower)
    vals = set()
    for s in shelf:
        m = re.search(r"(\d+(\.\d+)?)\s*(year|years|month|months|day|days)", s)
        if m:
            vals.add(m.group(0))
    if len(vals) >= 2:
        issues.append({"severity": "critical", "title": "Conflicting shelf life", "detail": f"Multiple shelf-life values found: {sorted(vals)}"})

    # sterilization method variations
    steril_methods = set()
    for pat in ["eto", "ethylene oxide", "gamma", "e-beam", "steam", "autoclave", "radiation"]:
        if pat in lower:
            steril_methods.add(pat)
    if len(steril_methods) >= 3:
        issues.append({"severity": "medium", "title": "Multiple sterilization methods mentioned", "detail": f"Sterilization terms found: {sorted(steril_methods)}"})

    # unsupported claims indicator
    if "no supporting anchor found" in lower:
        issues.append({"severity": "high", "title": "Unsupported statements", "detail": "Some statements appear to lack supporting evidence anchors."})

    # Build report
    md = ["## Consistency Guardian Report", ""]
    if not issues:
        md.append("No major consistency issues detected by heuristic checks.")
        return "\n".join(md)

    md.append(f"Detected issues: **{len(issues)}**")
    md.append("")
    md.append("| Severity | Issue | Detail |")
    md.append("|---|---|---|")
    for it in issues:
        md.append(f"| {it['severity']} | {it['title']} | {it['detail'].replace('|','\\|')} |")

    md.append("")
    md.append("### Recommended Actions")
    md.append("- Review flagged sections and harmonize terminology and numeric values.")
    md.append("- Use Evidence Mapper to confirm that key claims are traceable to OCR anchors.")
    return "\n".join(md)


def risk_radar_run(summary_text: str, evidence_results: Optional[List[dict]] = None) -> Tuple[dict, str]:
    """
    Produces domain scores 0-100 (higher = higher attention needed).
    Hybrid heuristic: missing signals and evidence coverage increase score.
    """
    text = summary_text or ""
    lower = text.lower()

    # Evidence coverage signal
    coverage = None
    if evidence_results:
        mapped = sum(1 for r in evidence_results if r.get("anchor_id"))
        coverage = mapped / max(1, len(evidence_results))

    domains = {
        "Device Description": 0,
        "Indications for Use": 0,
        "Predicate Comparison": 0,
        "Performance Testing": 0,
        "Biocompatibility": 0,
        "Sterilization/Shelf-life": 0,
        "Software/Cybersecurity": 0,
        "Labeling/IFU": 0,
        "Post-market Signals": 0,
    }

    def missing_penalty(keywords: List[str], weight: int):
        return weight if not any(k in lower for k in keywords) else 0

    domains["Device Description"] += missing_penalty(["device description", "overview", "device"], 35)
    domains["Indications for Use"] += missing_penalty(["indications", "intended use"], 40)
    domains["Predicate Comparison"] += missing_penalty(["predicate", "substantial equivalence", "equivalent"], 45)
    domains["Performance Testing"] += missing_penalty(["performance", "bench", "verification", "validation", "test"], 40)
    domains["Biocompatibility"] += missing_penalty(["biocompat", "iso 10993"], 45)
    domains["Sterilization/Shelf-life"] += missing_penalty(["steril", "shelf life", "packaging"], 45)
    domains["Software/Cybersecurity"] += missing_penalty(["software", "cyber", "security", "sbom"], 35)
    domains["Labeling/IFU"] += missing_penalty(["label", "ifu", "instructions for use"], 35)

    # Post-market: if datasets show hits, raise attention
    dv = st.session_state.get("data.device_view", {}) or {}
    mdr_count = dv.get("mdr_count", 0) or 0
    recall_sev = dv.get("recall_max_class", 0) or 0
    if mdr_count > 0:
        domains["Post-market Signals"] += min(60, 10 + int(math.log1p(mdr_count) * 15))
    if recall_sev:
        domains["Post-market Signals"] += 20 + (recall_sev * 10)

    # Evidence coverage penalty
    if coverage is not None:
        if coverage < 0.4:
            for k in domains:
                domains[k] += 10
        elif coverage < 0.65:
            for k in domains:
                domains[k] += 5

    # clamp 0..100
    for k in domains:
        domains[k] = int(max(0, min(100, domains[k])))

    # Markdown register
    md = ["## Regulatory Risk Radar", ""]
    md.append(f"- Evidence coverage signal: **{coverage:.2f}**" if coverage is not None else "- Evidence coverage signal: *(not available)*")
    md.append("")
    md.append("| Domain | Attention Score (0-100) | Rationale (brief) |")
    md.append("|---|---:|---|")
    for k, v in domains.items():
        rationale = "Missing or weak coverage in summary." if v >= 60 else ("Some gaps detected." if v >= 35 else "Appears reasonably covered.")
        if k == "Post-market Signals" and (mdr_count or recall_sev):
            rationale = f"Dataset signals: MDR={mdr_count}, RecallClassMax={recall_sev}."
        md.append(f"| {k} | {v} | {rationale} |")

    md.append("")
    md.append("### Priority Reading Plan (Suggested)")
    md.append("1. Review domains with the highest scores first.")
    md.append("2. Use Evidence Mapper to confirm traceability for high-impact claims.")
    md.append("3. Convert gaps into concrete reviewer follow-up questions.")
    return domains, "\n".join(md)


def plot_radar(domains: dict):
    if go is None:
        st.info("plotly is not installed; radar visualization unavailable.")
        return
    labels = list(domains.keys())
    values = list(domains.values())
    # close loop
    labels2 = labels + [labels[0]]
    values2 = values + [values[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=values2, theta=labels2, fill="toself", name="Attention Score"))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False,
        margin=dict(l=30, r=30, t=30, b=30),
        height=360,
    )
    st.plotly_chart(fig, use_container_width=True)


# -----------------------------
# 12) UI Blocks
# -----------------------------
def render_header():
    col1, col2, col3, col4, col5 = st.columns([2.4, 1, 1, 2.2, 1.2], vertical_alignment="center")
    with col1:
        st.markdown(f"## {APP_TITLE}")
        st.caption("Single-container Streamlit app for multi-PDF ingestion, OCR, multi-agent review, WOW AI features, dashboards, and audit-ready traceability.")

    with col2:
        mode = st.selectbox(t("mode"), ["command_center", "note_keeper"], index=0 if st.session_state["ui.mode"] == "command_center" else 1,
                            format_func=lambda x: t("command_center") if x == "command_center" else t("note_keeper"))
        st.session_state["ui.mode"] = mode

    with col3:
        theme = st.selectbox(t("theme"), ["dark", "light"], index=0 if st.session_state["ui.theme"] == "dark" else 1,
                             format_func=lambda x: t("dark") if x == "dark" else t("light"))
        st.session_state["ui.theme"] = theme
        low_res = st.toggle(t("low_resource"), value=st.session_state.get("ui.low_resource_mode", False))
        st.session_state["ui.low_resource_mode"] = low_res

    with col4:
        lang = st.selectbox(t("language"), ["en", "zh-TW"], index=0 if st.session_state["ui.lang"] == "en" else 1)
        st.session_state["ui.lang"] = lang

        style_ids = list(PAINTER_STYLES.keys())
        style_names = [PAINTER_STYLES[s]["name"] for s in style_ids]
        current = st.session_state.get("ui.painter_style", "cyberpunk")
        idx = style_ids.index(current) if current in style_ids else 0
        chosen = st.selectbox(t("painter_style"), style_ids, index=idx, format_func=lambda x: PAINTER_STYLES[x]["name"])
        st.session_state["ui.painter_style"] = chosen

    with col5:
        if st.button(t("jackpot")):
            # deterministic-ish rotation
            seed = (st.session_state.get("ui.jackpot_seed", 0) + 1) % len(PAINTER_STYLES)
            st.session_state["ui.jackpot_seed"] = seed
            style = list(PAINTER_STYLES.keys())[seed]
            st.session_state["ui.painter_style"] = style
            safe_event("ui", "info", f"Jackpot style selected: {PAINTER_STYLES[style]['name']}")

        st.session_state["ui.preserve_prefs_on_purge"] = st.checkbox(
            "Preserve UI prefs on purge",
            value=st.session_state.get("ui.preserve_prefs_on_purge", True),
        )


def render_status_strip():
    # Build chips
    srcs = {p: provider_key_source(p) for p in PROVIDERS}
    ok = "ok"
    warn = "warn"
    err = "err"

    def chip(label: str, status: str):
        st.markdown(f"<span class='wow-chip {status}'>{label}</span>", unsafe_allow_html=True)

    st.markdown("<div class='wow-panel'>", unsafe_allow_html=True)

    # Provider chips
    for p in PROVIDERS:
        src = srcs[p]
        status = ok if src in ["env", "session"] else err
        label = f"{p.upper()}: {src}"
        chip(label, status)

    # Workload chips
    reg = st.session_state.get("docs.registry", [])
    sel = st.session_state.get("docs.queue.selected_ids", set())
    trimmed = st.session_state.get("docs.trim.outputs", {})
    consolidated = st.session_state.get("docs.consolidated_markdown", "") or ""
    chip(f"PDFs: {len(reg)} ingested / {len(sel)} selected", ok if len(sel) else warn)
    chip(f"Trimmed: {len(trimmed)}", ok if len(trimmed) else warn)
    chip(f"OCR chars: {len(consolidated)} (~{approx_tokens(consolidated)} tok)", ok if consolidated else warn)

    # Pipeline statuses
    ps = st.session_state.get("obs.pipeline_state", {})
    for node in ["ingestion", "trim", "ocr", "consolidation", "agents", "summary", "wow_ai"]:
        stt = ps.get(node, {}).get("status", "idle")
        status = ok if stt == "done" else (warn if stt in ["running", "warn"] else err if stt == "error" else warn)
        chip(f"{node}: {stt}", status)

    # Mana bar (simple)
    mana = min(100, int((len(consolidated) / 8000) + (len(st.session_state.get("agents.timeline", {}).get("nodes", [])) * 8)))
    st.progress(mana / 100.0, text=f"Review Mana: {mana}/100")

    st.markdown("</div>", unsafe_allow_html=True)


def render_left_pane():
    st.markdown(f"<div class='wow-panel'><span class='wow-accent'>{t('ingestion')}</span></div>", unsafe_allow_html=True)
    with st.expander(t("ingestion"), expanded=True):
        uploaded = st.file_uploader(t("upload_pdfs"), type=["pdf"], accept_multiple_files=True)
        paths = st.text_area(t("paths"), placeholder="/path/to/file1.pdf\n/path/to/file2.pdf")
        if st.button(t("register_files")):
            set_pipeline_state("ingestion", "running", "Registering files...")
            if uploaded:
                register_uploaded_files(uploaded)
            if paths.strip():
                register_file_paths(paths)
            ensure_scanned_metadata()
            set_pipeline_state("ingestion", "done", f"Registry size: {len(st.session_state['docs.registry'])}")

    with st.expander(t("queue"), expanded=True):
        ensure_scanned_metadata()
        reg = st.session_state.get("docs.registry", [])
        if pd is not None and reg:
            df = pd.DataFrame([{
                "selected": f["id"] in st.session_state["docs.queue.selected_ids"],
                "name": f["name"],
                "source": f["source"],
                "size": human_size(f["size"]),
                "pages": f.get("page_count"),
                "health": f.get("health"),
                "id": f["id"],
            } for f in reg])
            edited = st.data_editor(
                df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "selected": st.column_config.CheckboxColumn(required=True),
                    "id": st.column_config.TextColumn(disabled=True),
                },
                disabled=["name", "source", "size", "pages", "health", "id"],
            )
            selected_ids = set(edited.loc[edited["selected"] == True, "id"].tolist())
            st.session_state["docs.queue.selected_ids"] = selected_ids
        else:
            if not reg:
                st.info("No PDFs registered yet.")
            else:
                st.write(reg)

        st.caption("Per-file trim overrides (optional):")
        sel = st.session_state.get("docs.queue.selected_ids", set())
        per = st.session_state.get("docs.trim.per_file_override", {})
        if sel:
            for fid in list(sel)[:10]:  # keep UI manageable
                name = next((f["name"] for f in reg if f["id"] == fid), fid)
                per[fid] = st.text_input(f"Override range — {name}", value=per.get(fid, ""), placeholder="e.g., 1-5, 10, 15-20")
            st.session_state["docs.trim.per_file_override"] = per
        else:
            st.caption("Select files to enable per-file overrides.")

    with st.expander(t("trim"), expanded=True):
        st.session_state["docs.trim.global_range"] = st.text_input(t("global_range"), value=st.session_state.get("docs.trim.global_range", "1-5"))
        policy = st.selectbox("Out-of-range policy", ["clip_with_warn", "skip_file", "block"], index=0)
        if st.button(t("execute_trim")):
            if not st.session_state.get("docs.queue.selected_ids"):
                st.warning("No files selected.")
            else:
                try:
                    _ = parse_page_ranges(st.session_state["docs.trim.global_range"])
                except Exception as e:
                    st.error(f"Invalid range: {e}")
                    return
                execute_trimming(policy_out_of_range=policy)

    with st.expander(t("ocr"), expanded=True):
        mode = st.selectbox(t("ocr_mode"), ["python_pack", "llm_ocr"],
                            format_func=lambda x: t("python_pack") if x == "python_pack" else t("llm_ocr"),
                            index=0 if st.session_state["docs.ocr.mode"] == "python_pack" else 1)
        st.session_state["docs.ocr.mode"] = mode

        if mode == "llm_ocr":
            st.session_state["docs.ocr.model"] = st.selectbox("Gemini model", GEMINI_MODELS, index=GEMINI_MODELS.index(st.session_state.get("docs.ocr.model", GEMINI_MODELS[0])))
            st.session_state["docs.ocr.prompt"] = st.text_area(t("ocr_prompt"), value=st.session_state.get("docs.ocr.prompt", ""), height=120)

        if st.button(t("execute_ocr")):
            if not st.session_state.get("docs.trim.outputs"):
                st.warning("Trim outputs not found. Run Trim first.")
            else:
                execute_ocr()

    with st.expander(t("consolidated"), expanded=True):
        aid = st.session_state.get("consolidated.artifact_id")
        if not aid and st.session_state.get("docs.consolidated_markdown"):
            aid = create_artifact(st.session_state["docs.consolidated_markdown"], fmt="markdown", metadata={"source": "ocr_consolidation"})
            st.session_state["consolidated.artifact_id"] = aid

        if not aid:
            st.info("No consolidated OCR artifact yet.")
            return

        tabs = st.tabs(["Text", "Markdown", "Diff", "Versions"])
        cur_text, cur_meta = artifact_get_current(aid)

        with tabs[0]:
            new_text = st.text_area("Edit consolidated text", value=cur_text, height=260)
            if st.button("Save consolidated edit"):
                artifact_add_version(aid, new_text, created_by="user_edit", metadata={"type": "consolidated_edit"}, parent_version_id=cur_meta.get("version_id"))
                st.session_state["docs.consolidated_markdown"] = new_text
                safe_event("artifact", "info", "Consolidated OCR edited and versioned.")
        with tabs[1]:
            st.markdown(markdown_highlight_keywords(cur_text, st.session_state.get("notes.keywords.palette", {})), unsafe_allow_html=True)
        with tabs[2]:
            versions = artifact_versions(aid)
            if len(versions) >= 2:
                prev = versions[-2]["content_text"]
                st.markdown(simple_diff(prev, cur_text), unsafe_allow_html=True)
            else:
                st.info("Need at least 2 versions for diff.")
        with tabs[3]:
            versions = artifact_versions(aid)
            for v in reversed(versions[-10:]):
                st.write(f"- {v['created_at']} | {v['created_by']} | {v['version_id'][:8]}")
            sel_vid = st.selectbox("Restore version", [v["version_id"] for v in versions][::-1])
            if st.button("Restore selected version"):
                st.session_state["artifacts"][aid]["current_version_id"] = sel_vid
                restored, _ = artifact_get_current(aid)
                st.session_state["docs.consolidated_markdown"] = restored
                safe_event("artifact", "warn", f"Restored consolidated version {sel_vid[:8]}.")

        st.download_button("Download consolidated markdown", data=cur_text.encode("utf-8"), file_name="consolidated_ocr.md", mime="text/markdown")


def render_agents_and_intelligence():
    # Load + validate agents.yaml
    load_agents_yaml()
    if st.session_state.get("agents.yaml.validated") is None:
        cfg = validate_agents_yaml(st.session_state.get("agents.yaml.raw", ""))
        st.session_state["agents.yaml.validated"] = cfg
        if cfg:
            st.session_state["agents.run.order"] = [a.id for a in cfg.agents]

    right_tabs = st.tabs([t("agent_orchestration"), t("macro_summary"), t("dynamic_skill"), t("wow_ai"), t("search"), t("dashboards")])

    # --- Agent Orchestration ---
    with right_tabs[0]:
        st.markdown("<div class='wow-panel'>", unsafe_allow_html=True)
        st.subheader(t("agents_yaml"))
        raw = st.text_area("agents.yaml (editable)", value=st.session_state.get("agents.yaml.raw", ""), height=240)
        st.session_state["agents.yaml.raw"] = raw

        colA, colB = st.columns([1, 2])
        with colA:
            if st.button(t("validate_yaml")):
                cfg = validate_agents_yaml(raw)
                st.session_state["agents.yaml.validated"] = cfg
                if cfg:
                    st.success("YAML validated.")
                    st.session_state["agents.run.order"] = [a.id for a in cfg.agents]
                    safe_event("agents", "info", "agents.yaml validated.")
                else:
                    st.error(st.session_state.get("agents.last_error", "Validation failed."))
                    safe_event("agents", "err", f"agents.yaml validation failed: {st.session_state.get('agents.last_error')}")
        with colB:
            cfg = st.session_state.get("agents.yaml.validated")
            if cfg:
                st.caption(f"Agents loaded: {len(cfg.agents)}")
            else:
                st.caption("No validated agent config yet.")

        st.divider()
        cfg = st.session_state.get("agents.yaml.validated")
        if not cfg:
            st.warning("Validate agents.yaml to run agents.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        # Select step
        agent_ids = [a.id for a in cfg.agents]
        selected_agent_id = st.selectbox("Select agent", agent_ids, format_func=lambda aid: next((a.name for a in cfg.agents if a.id == aid), aid))
        agent = next(a for a in cfg.agents if a.id == selected_agent_id)

        # Overrides
        ov = st.session_state["agents.step.overrides"].setdefault(agent.id, {})
        st.markdown("#### Step Overrides (before run)")
        c1, c2, c3 = st.columns(3)
        with c1:
            ov["provider"] = st.selectbox("Provider", PROVIDERS, index=PROVIDERS.index(ov.get("provider", agent.provider)))
        with c2:
            model_list = SUPPORTED_MODELS.get(ov["provider"], [])
            # allow custom by selectbox + manual
            ov["model"] = st.selectbox("Model", model_list, index=model_list.index(ov.get("model", agent.model)) if ov.get("model", agent.model) in model_list else 0)
        with c3:
            ov["max_tokens"] = st.number_input("max_tokens", min_value=256, max_value=32000, value=int(ov.get("max_tokens", agent.max_tokens or DEFAULT_MAX_TOKENS)), step=256)

        ov["temperature"] = st.slider("temperature", 0.0, 1.0, float(ov.get("temperature", agent.temperature if agent.temperature is not None else DEFAULT_TEMPERATURE)), 0.05)
        ov["system_prompt"] = st.text_area("System prompt", value=ov.get("system_prompt", agent.system_prompt or ""), height=120)
        ov["user_prompt"] = st.text_area("User prompt", value=ov.get("user_prompt", agent.user_prompt or ""), height=120)
        st.session_state["agents.step.overrides"][agent.id] = ov

        # Input builder
        st.markdown("#### Input Builder")
        consolidated = st.session_state.get("docs.consolidated_markdown", "") or ""
        consolidated_aid = st.session_state.get("consolidated.artifact_id")
        prev_agent_ids = [a.id for a in cfg.agents if a.id != agent.id and a.id in st.session_state.get("agents.step.outputs", {})]
        source_options = ["consolidated_ocr", "previous_agent_output", "manual_paste", "combined"]
        src = st.selectbox("Input source", source_options)
        context_parts = []

        manual = ""
        if src == "consolidated_ocr":
            context_parts.append(consolidated)
        elif src == "previous_agent_output":
            if not prev_agent_ids:
                st.info("No previous agent outputs yet.")
            else:
                pid = st.selectbox("Select previous agent output", prev_agent_ids, format_func=lambda aid: next((a.name for a in cfg.agents if a.id == aid), aid))
                out_aid = st.session_state["agents.step.outputs"][pid]
                prev_text, _ = artifact_get_current(out_aid)
                context_parts.append(prev_text)
        elif src == "manual_paste":
            manual = st.text_area("Paste manual input", height=160)
            context_parts.append(manual)
        else:
            # combined
            include_consolidated = st.checkbox("Include consolidated OCR", value=True)
            include_prev = st.checkbox("Include previous agent output", value=True)
            include_manual = st.checkbox("Include manual paste", value=False)
            if include_consolidated:
                context_parts.append(consolidated)
            if include_prev and prev_agent_ids:
                pid = st.selectbox("Previous output", prev_agent_ids, format_func=lambda aid: next((a.name for a in cfg.agents if a.id == aid), aid))
                out_aid = st.session_state["agents.step.outputs"][pid]
                prev_text, _ = artifact_get_current(out_aid)
                context_parts.append(prev_text)
            if include_manual:
                manual = st.text_area("Manual input", height=120)
                context_parts.append(manual)

        context = "\n\n".join([p for p in context_parts if p and p.strip()])

        st.caption(f"Context size: {len(context)} chars (~{approx_tokens(context)} tok est)")

        # Execute agent
        if st.button(t("run_agent")):
            if not context.strip():
                st.error("Empty context. Provide input source content first.")
            else:
                try:
                    set_pipeline_state("agents", "running", f"Running agent {agent.id}...")
                    out, meta = run_agent(agent, context=context, overrides=ov)
                    # Save artifact
                    artifact_id = create_artifact(out, fmt="markdown", metadata=meta)
                    st.session_state["agents.step.outputs"][agent.id] = artifact_id
                    # timeline node
                    src_node = timeline_add_node("agent_run", f"{agent.name}", artifact_id, meta)
                    # edge: from consolidated node if present
                    if consolidated_aid:
                        # ensure consolidated is also a timeline node
                        # create only once
                        if not st.session_state.get("timeline.consolidated_node_id"):
                            cn = timeline_add_node("ocr_consolidated", "Consolidated OCR", consolidated_aid, {"chars": len(consolidated)})
                            st.session_state["timeline.consolidated_node_id"] = cn
                        timeline_add_edge(st.session_state["timeline.consolidated_node_id"], src_node, "context")
                    set_pipeline_state("agents", "done", f"Agent {agent.id} done.")
                    safe_event("agents", "info", f"Agent run completed: {agent.id}")
                    st.success("Agent completed.")
                except Exception as e:
                    set_pipeline_state("agents", "error", str(e))
                    safe_event("agents", "err", f"Agent failed: {e}")
                    st.error(str(e))

        # Output editor + commit
        out_aid = st.session_state.get("agents.step.outputs", {}).get(agent.id)
        if out_aid:
            st.markdown("#### Agent Output")
            out_tabs = st.tabs(["Text", "Markdown", "Diff", "Versions"])
            out_text, out_meta = artifact_get_current(out_aid)
            with out_tabs[0]:
                edited = st.text_area("Edit agent output", value=out_text, height=260)
                csave, ccommit = st.columns([1, 1])
                with csave:
                    if st.button("Save output edit"):
                        artifact_add_version(out_aid, edited, created_by="user_edit", metadata={"type": "agent_output_edit"}, parent_version_id=out_meta.get("version_id"))
                        safe_event("artifact", "info", f"Edited agent output versioned: {agent.id}")
                with ccommit:
                    if st.button(t("commit_next")):
                        # Commit means: create a timeline node indicating "handoff committed"
                        node = timeline_add_node("handoff_commit", f"Handoff committed from {agent.name}", out_aid, {"agent_id": agent.id})
                        # If there is a last agent node, connect
                        nodes = st.session_state["agents.timeline"]["nodes"]
                        # connect from latest agent_run node for same artifact if possible
                        latest_agent_node = next((n for n in reversed(nodes) if n.get("artifact_id") == out_aid and n.get("kind") == "agent_run"), None)
                        if latest_agent_node:
                            timeline_add_edge(latest_agent_node["node_id"], node, "commit")
                        safe_event("agents", "info", f"Committed output as next input: {agent.id}")
                        st.success("Committed. Use this output as input for the next step via 'previous agent output'.")
            with out_tabs[1]:
                st.markdown(markdown_highlight_keywords(out_text, st.session_state.get("notes.keywords.palette", {})), unsafe_allow_html=True)
            with out_tabs[2]:
                versions = artifact_versions(out_aid)
                if len(versions) >= 2:
                    prev = versions[-2]["content_text"]
                    st.markdown(simple_diff(prev, out_text), unsafe_allow_html=True)
                else:
                    st.info("Need at least 2 versions for diff.")
            with out_tabs[3]:
                versions = artifact_versions(out_aid)
                for v in reversed(versions[-10:]):
                    st.write(f"- {v['created_at']} | {v['created_by']} | {v['version_id'][:8]}")
                sel_vid = st.selectbox("Restore version (agent output)", [v["version_id"] for v in versions][::-1], key=f"restore_{agent.id}")
                if st.button("Restore selected (agent output)", key=f"restore_btn_{agent.id}"):
                    st.session_state["artifacts"][out_aid]["current_version_id"] = sel_vid
                    safe_event("artifact", "warn", f"Restored agent {agent.id} output version {sel_vid[:8]}.")

        st.markdown("</div>", unsafe_allow_html=True)

    # --- Macro Summary ---
    with right_tabs[1]:
        cfg = st.session_state.get("agents.yaml.validated")
        st.subheader(t("macro_summary"))

        # Choose an agent to use as macro-summary engine (default: agent named macro)
        macro_agent = None
        if cfg:
            macro_agent = next((a for a in cfg.agents if "macro" in a.name.lower() or "3000" in (a.system_prompt or "").lower()), None)
            if not macro_agent:
                macro_agent = cfg.agents[-1]

        st.caption(f"Macro agent: {macro_agent.name if macro_agent else 'N/A'}")

        # Source selection
        src_opts = ["consolidated_ocr", "agent_output"]
        src = st.selectbox("Macro summary input source", src_opts, index=0)
        context = ""
        if src == "consolidated_ocr":
            context = st.session_state.get("docs.consolidated_markdown", "") or ""
        else:
            cfg = st.session_state.get("agents.yaml.validated")
            outs = st.session_state.get("agents.step.outputs", {})
            if cfg and outs:
                choices = list(outs.keys())
                aid_sel = st.selectbox("Select agent output", choices, format_func=lambda x: next((a.name for a in cfg.agents if a.id == x), x))
                art_id = outs[aid_sel]
                context, _ = artifact_get_current(art_id)
            else:
                st.info("No agent outputs available.")

        # Controls
        provider = st.selectbox("Provider", PROVIDERS, index=0)
        model = st.selectbox("Model", SUPPORTED_MODELS.get(provider, []), index=0)
        max_tokens = st.number_input("max_tokens", min_value=256, max_value=32000, value=DEFAULT_MAX_TOKENS, step=256)
        temperature = st.slider("temperature", 0.0, 1.0, 0.2, 0.05)

        system_prompt = st.text_area(
            "System prompt (macro)",
            value=(macro_agent.system_prompt if macro_agent else "You are a regulatory writing engine. Output 3000–4000 words in Markdown."),
            height=120,
        )
        user_prompt = st.text_area(
            "User prompt (macro)",
            value=(macro_agent.user_prompt if macro_agent else "Write a comprehensive 3000–4000 word FDA-style analytical review report based strictly on the provided content."),
            height=120,
        )

        if st.button("Generate Macro Summary"):
            if not context.strip():
                st.error("No context.")
            else:
                try:
                    set_pipeline_state("summary", "running", "Generating macro summary...")
                    out, meta = llm_execute(provider, model, system_prompt, user_prompt, context, max_tokens, temperature)
                    meta["kind"] = "macro_summary"
                    if not st.session_state.get("summary.artifact_id"):
                        sid = create_artifact(out, fmt="markdown", metadata=meta)
                        st.session_state["summary.artifact_id"] = sid
                    else:
                        sid = st.session_state["summary.artifact_id"]
                        cur, curm = artifact_get_current(sid)
                        artifact_add_version(sid, out, created_by="macro_agent", metadata=meta, parent_version_id=curm.get("version_id"))
                    timeline_add_node("macro_summary", "Macro Summary", st.session_state["summary.artifact_id"], meta)
                    set_pipeline_state("summary", "done", "Macro summary generated.")
                    safe_event("summary", "info", "Macro summary generated.")
                    st.success("Macro summary generated.")
                except Exception as e:
                    set_pipeline_state("summary", "error", str(e))
                    safe_event("summary", "err", f"Macro summary failed: {e}")
                    st.error(str(e))

        # Editor
        sid = st.session_state.get("summary.artifact_id")
        if sid:
            st.markdown("#### Macro Summary Editor")
            tabs = st.tabs(["Text", "Markdown", "Diff", "Versions"])
            s_text, s_meta = artifact_get_current(sid)
            with tabs[0]:
                edited = st.text_area("Edit macro summary", value=s_text, height=300)
                if st.button("Save summary edit"):
                    artifact_add_version(sid, edited, created_by="user_edit", metadata={"type": "summary_edit"}, parent_version_id=s_meta.get("version_id"))
                    safe_event("summary", "info", "Macro summary edited.")
            with tabs[1]:
                st.markdown(markdown_highlight_keywords(s_text, st.session_state.get("notes.keywords.palette", {})), unsafe_allow_html=True)
            with tabs[2]:
                versions = artifact_versions(sid)
                if len(versions) >= 2:
                    prev = versions[-2]["content_text"]
                    st.markdown(simple_diff(prev, s_text), unsafe_allow_html=True)
                else:
                    st.info("Need at least 2 versions for diff.")
            with tabs[3]:
                versions = artifact_versions(sid)
                for v in reversed(versions[-10:]):
                    st.write(f"- {v['created_at']} | {v['created_by']} | {v['version_id'][:8]}")
                sel_vid = st.selectbox("Restore version (summary)", [v["version_id"] for v in versions][::-1], key="restore_summary")
                if st.button("Restore selected (summary)"):
                    st.session_state["artifacts"][sid]["current_version_id"] = sel_vid
                    safe_event("summary", "warn", f"Restored summary version {sel_vid[:8]}.")

            # Persistent prompt
            st.markdown("#### " + t("persistent_prompt"))
            st.session_state["summary.persistent_prompt"] = st.text_area("Prompt to revise current summary", value=st.session_state.get("summary.persistent_prompt", ""), height=90)
            if st.button(t("run_persistent_prompt")):
                prompt = st.session_state.get("summary.persistent_prompt", "")
                if not prompt.strip():
                    st.warning("Empty prompt.")
                else:
                    try:
                        set_pipeline_state("summary", "running", "Applying persistent prompt...")
                        cur_text, curm = artifact_get_current(sid)
                        sys_p = "You are revising an FDA-style regulatory report. Preserve factuality. Update the report per instruction."
                        usr_p = prompt.strip()
                        out, meta = llm_execute(provider, model, sys_p, usr_p, cur_text, max_tokens, temperature)
                        artifact_add_version(sid, out, created_by="persistent_prompt", metadata={"kind": "persistent_prompt", **meta}, parent_version_id=curm.get("version_id"))
                        timeline_add_node("summary_revision", "Summary Revision (Persistent Prompt)", sid, {"prompt_hash": sha256_hex(prompt), **meta})
                        set_pipeline_state("summary", "done", "Persistent prompt applied.")
                        safe_event("summary", "info", "Persistent prompt applied.")
                        st.success("Updated.")
                    except Exception as e:
                        set_pipeline_state("summary", "error", str(e))
                        safe_event("summary", "err", f"Persistent prompt failed: {e}")
                        st.error(str(e))

            st.download_button("Download macro summary", data=s_text.encode("utf-8"), file_name="macro_summary.md", mime="text/markdown")
        else:
            st.info("No macro summary artifact yet.")

    # --- Dynamic Skill ---
    with right_tabs[2]:
        st.subheader(t("dynamic_skill"))
        sid = st.session_state.get("summary.artifact_id")
        if not sid:
            st.info("Generate a macro summary first.")
        else:
            desc = st.text_area(t("skill_desc"), value=st.session_state.get("skills.last_description", ""), height=160)
            st.session_state["skills.last_description"] = desc
            provider = st.selectbox("Provider (skill)", PROVIDERS, index=0, key="skill_provider")
            model = st.selectbox("Model (skill)", SUPPORTED_MODELS.get(provider, []), index=0, key="skill_model")
            max_tokens = st.number_input("max_tokens (skill)", min_value=256, max_value=32000, value=DEFAULT_MAX_TOKENS, step=256, key="skill_tokens")
            temperature = st.slider("temperature (skill)", 0.0, 1.0, 0.2, 0.05, key="skill_temp")

            if st.button(t("run_skill")):
                if not desc.strip():
                    st.error("Skill description is empty.")
                else:
                    try:
                        set_pipeline_state("wow_ai", "running", "Executing skill...")
                        summary_text, _ = artifact_get_current(sid)
                        system_prompt = desc.strip()
                        user_prompt = "Apply the skill precisely to the provided summary. Output in Markdown."
                        out, meta = llm_execute(provider, model, system_prompt, user_prompt, summary_text, max_tokens, temperature)
                        aid = create_artifact(out, fmt="markdown", metadata={"kind": "skill_output", **meta, "skill_hash": sha256_hex(desc)})
                        st.session_state["skills.outputs"].append(aid)
                        timeline_add_node("skill_output", "Dynamic Skill Output", aid, {"skill_hash": sha256_hex(desc), **meta})
                        set_pipeline_state("wow_ai", "done", "Skill executed.")
                        safe_event("skills", "info", "Dynamic skill executed.")
                        st.success("Skill executed.")
                    except Exception as e:
                        set_pipeline_state("wow_ai", "error", str(e))
                        safe_event("skills", "err", f"Skill failed: {e}")
                        st.error(str(e))

            if st.session_state.get("skills.outputs"):
                st.markdown("#### Skill Result Cards")
                for i, aid in enumerate(reversed(st.session_state["skills.outputs"][-5:]), start=1):
                    text, _ = artifact_get_current(aid)
                    with st.expander(f"Skill Output #{i}", expanded=False):
                        st.markdown(markdown_highlight_keywords(text, st.session_state.get("notes.keywords.palette", {})), unsafe_allow_html=True)
                        st.download_button(f"Download Skill Output #{i}", data=text.encode("utf-8"), file_name=f"skill_output_{i}.md", mime="text/markdown")

    # --- WOW AI ---
    with right_tabs[3]:
        st.subheader(t("wow_ai"))
        sid = st.session_state.get("summary.artifact_id")
        if not sid:
            st.info("Generate a macro summary first.")
            return

        summary_text, _ = artifact_get_current(sid)

        wow_tabs = st.tabs([t("evidence_mapper"), t("consistency_guardian"), t("risk_radar")])

        # Evidence Mapper
        with wow_tabs[0]:
            target = st.selectbox("Map evidence for", ["macro_summary", "selected_agent_output"], index=0)
            target_text = summary_text
            if target == "selected_agent_output":
                cfg = st.session_state.get("agents.yaml.validated")
                outs = st.session_state.get("agents.step.outputs", {})
                if cfg and outs:
                    choices = list(outs.keys())
                    aid_sel = st.selectbox("Agent output", choices, format_func=lambda x: next((a.name for a in cfg.agents if a.id == x), x))
                    art_id = outs[aid_sel]
                    target_text, _ = artifact_get_current(art_id)
                else:
                    st.info("No agent outputs available; using macro summary.")
                    target_text = summary_text

            if st.button(t("run_evidence")):
                try:
                    set_pipeline_state("wow_ai", "running", "Evidence mapping...")
                    md, rows = evidence_mapper_run(target_text)
                    aid = create_artifact(md, fmt="markdown", metadata={"kind": "evidence_map", "rows": len(rows)})
                    st.session_state["wow.evidence.artifact_id"] = aid
                    st.session_state["wow.evidence.rows"] = rows
                    timeline_add_node("wow_evidence_map", "WOW Evidence Map", aid, {"rows": len(rows)})
                    set_pipeline_state("wow_ai", "done", "Evidence mapping complete.")
                    safe_event("wow_ai", "info", "Evidence mapping completed.")
                    st.success("Evidence mapping complete.")
                except Exception as e:
                    set_pipeline_state("wow_ai", "error", str(e))
                    safe_event("wow_ai", "err", f"Evidence mapping failed: {e}")
                    st.error(str(e))

            aid = st.session_state.get("wow.evidence.artifact_id")
            if aid:
                md, _ = artifact_get_current(aid)
                st.markdown(md, unsafe_allow_html=True)
                rows = st.session_state.get("wow.evidence.rows", [])
                if pd is not None and rows:
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                st.download_button("Download evidence map", data=md.encode("utf-8"), file_name="evidence_map.md", mime="text/markdown")

        # Consistency Guardian
        with wow_tabs[1]:
            if st.button(t("run_consistency")):
                try:
                    set_pipeline_state("wow_ai", "running", "Consistency checking...")
                    md = consistency_guardian_run(summary_text)
                    aid = create_artifact(md, fmt="markdown", metadata={"kind": "consistency_report"})
                    st.session_state["wow.consistency.artifact_id"] = aid
                    timeline_add_node("wow_consistency", "WOW Consistency Report", aid, {})
                    set_pipeline_state("wow_ai", "done", "Consistency check complete.")
                    safe_event("wow_ai", "info", "Consistency check completed.")
                    st.success("Consistency check complete.")
                except Exception as e:
                    set_pipeline_state("wow_ai", "error", str(e))
                    safe_event("wow_ai", "err", f"Consistency check failed: {e}")
                    st.error(str(e))

            aid = st.session_state.get("wow.consistency.artifact_id")
            if aid:
                md, _ = artifact_get_current(aid)
                st.markdown(md, unsafe_allow_html=True)
                st.download_button("Download consistency report", data=md.encode("utf-8"), file_name="consistency_report.md", mime="text/markdown")

        # Risk Radar
        with wow_tabs[2]:
            evidence_rows = st.session_state.get("wow.evidence.rows")
            if st.button(t("run_risk")):
                try:
                    set_pipeline_state("wow_ai", "running", "Generating risk radar...")
                    domains, md = risk_radar_run(summary_text, evidence_results=evidence_rows)
                    aid = create_artifact(md, fmt="markdown", metadata={"kind": "risk_radar"})
                    st.session_state["wow.risk.artifact_id"] = aid
                    st.session_state["wow.risk.domains"] = domains
                    timeline_add_node("wow_risk_radar", "WOW Risk Radar", aid, {"domains": domains})
                    set_pipeline_state("wow_ai", "done", "Risk radar complete.")
                    safe_event("wow_ai", "info", "Risk radar generated.")
                    st.success("Risk radar complete.")
                except Exception as e:
                    set_pipeline_state("wow_ai", "error", str(e))
                    safe_event("wow_ai", "err", f"Risk radar failed: {e}")
                    st.error(str(e))

            aid = st.session_state.get("wow.risk.artifact_id")
            if aid:
                md, _ = artifact_get_current(aid)
                domains = st.session_state.get("wow.risk.domains", {})
                if domains:
                    plot_radar(domains)
                st.markdown(md, unsafe_allow_html=True)
                st.download_button("Download risk radar", data=md.encode("utf-8"), file_name="risk_radar.md", mime="text/markdown")

    # --- Cross-dataset Search ---
    with right_tabs[4]:
        st.subheader(t("datasets"))
        if not st.session_state.get("data.loaded"):
            if st.button("Load datasets"):
                load_datasets_best_effort()

        st.subheader(t("search"))
        query = st.text_input("Query", value=st.session_state.get("data.last_query", ""))
        if st.button("Search"):
            st.session_state["data.last_query"] = query
            res = fuzzy_search_all(query)
            st.session_state["data.last_results"] = res
            safe_event("search", "info", f"Search executed: '{query}'")

        res = st.session_state.get("data.last_results", {}) or {}
        if pd is not None and res:
            for name, df in res.items():
                st.markdown(f"### {name.upper()} (top results)")
                if df is None:
                    st.info("No data.")
                elif getattr(df, "empty", True):
                    st.info("No matches.")
                else:
                    st.dataframe(df.head(25), use_container_width=True)

        # 360 view (minimal, user-selectable)
        st.markdown("### 360° Device View (minimal)")
        dv = st.session_state.get("data.device_view", {}) or {}
        st.caption("This v2.6 code includes a minimal placeholder for device view aggregation. Expand with your actual dataset schema.")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("MDR count", dv.get("mdr_count", 0))
        with c2:
            st.metric("Max Recall Class", dv.get("recall_max_class", 0))
        with c3:
            st.metric("GUDID flags", dv.get("gudid_flags", 0))

    # --- Dashboards ---
    with right_tabs[5]:
        dash_tabs = st.tabs([t("mission_control"), t("timeline"), t("logs"), t("export")])

        with dash_tabs[0]:
            st.subheader(t("mission_control"))
            ps = st.session_state.get("obs.pipeline_state", {})
            st.markdown("#### Pipeline State Machine")
            if pd is not None:
                rows = []
                for k, v in ps.items():
                    rows.append({"node": k, "status": v.get("status"), "last_update": v.get("last_update"), "detail": v.get("detail")})
                if rows:
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                else:
                    st.info("No pipeline state yet.")
            else:
                st.write(ps)

            st.markdown("#### Provider Telemetry")
            m = st.session_state.get("obs.metrics", {})
            calls = {p: int(m.get(f"{p}.calls", 0)) for p in PROVIDERS}
            errs = {p: int(m.get(f"{p}.errors", 0)) for p in PROVIDERS}
            st.write("Calls:", calls)
            st.write("Errors:", errs)
            st.write("Approx memory footprint:", human_size(mem_estimate_bytes()))
            if mem_estimate_bytes() > 600 * 1024 * 1024:
                st.warning("Memory estimate is high for a Spaces container. Consider low-resource mode, trimming fewer pages, or reducing OCR scope.")

        with dash_tabs[1]:
            st.subheader(t("timeline"))
            tl = st.session_state.get("agents.timeline", {"nodes": [], "edges": []})
            if pd is not None:
                st.markdown("#### Nodes")
                st.dataframe(pd.DataFrame(tl["nodes"]), use_container_width=True, hide_index=True)
                st.markdown("#### Edges")
                st.dataframe(pd.DataFrame(tl["edges"]), use_container_width=True, hide_index=True)
            else:
                st.write(tl)

        with dash_tabs[2]:
            st.subheader(t("logs"))
            events = st.session_state.get("obs.events", [])
            if pd is not None and events:
                df = pd.DataFrame(events)
                sev = st.multiselect("Severity filter", ["info", "warn", "err"], default=["info", "warn", "err"])
                comp = st.text_input("Component contains", value="")
                df2 = df[df["severity"].isin(sev)]
                if comp.strip():
                    df2 = df2[df2["component"].astype(str).str.contains(comp.strip(), case=False, na=False)]
                st.dataframe(df2, use_container_width=True, hide_index=True)
                st.download_button("Download logs (json)", data=json.dumps(events, ensure_ascii=False, indent=2).encode("utf-8"),
                                   file_name="session_logs.json", mime="application/json")
            else:
                st.write(events or "No logs yet.")

        with dash_tabs[3]:
            st.subheader(t("export"))
            st.caption("Export a session bundle (redacted logs, consolidated OCR, summary, and WOW AI outputs where available).")
            if st.button("Build export bundle"):
                bundle = {}
                # consolidated
                caid = st.session_state.get("consolidated.artifact_id")
                if caid:
                    ctext, _ = artifact_get_current(caid)
                    bundle["consolidated_ocr.md"] = ctext
                # summary
                sid = st.session_state.get("summary.artifact_id")
                if sid:
                    stext, _ = artifact_get_current(sid)
                    bundle["macro_summary.md"] = stext
                # evidence/consistency/risk
                for k, fname in [
                    ("wow.evidence.artifact_id", "evidence_map.md"),
                    ("wow.consistency.artifact_id", "consistency_report.md"),
                    ("wow.risk.artifact_id", "risk_radar.md"),
                ]:
                    aid = st.session_state.get(k)
                    if aid:
                        text, _ = artifact_get_current(aid)
                        bundle[fname] = text

                # logs (redacted: no keys already)
                bundle["session_logs.json"] = json.dumps(st.session_state.get("obs.events", []), ensure_ascii=False, indent=2)

                st.session_state["obs.export.ready"] = {"built_at": now_taipei_str(), "files": list(bundle.keys())}
                # Provide a combined markdown and json downloads
                st.success(f"Bundle built with {len(bundle)} files.")
                # Show file list and offer individual downloads
                for fn, content in bundle.items():
                    mime = "text/markdown" if fn.endswith(".md") else "application/json"
                    st.download_button(f"Download {fn}", data=(content.encode("utf-8") if isinstance(content, str) else content),
                                       file_name=fn, mime=mime)


def render_note_keeper():
    st.markdown("<div class='wow-panel'>", unsafe_allow_html=True)
    st.subheader(t("note_keeper"))
    st.caption("Paste text/markdown → transform into organized Markdown → edit → run AI Magics + keyword coloring.")
    st.markdown("</div>", unsafe_allow_html=True)

    c1, c2 = st.columns([1.2, 1])
    with c1:
        st.session_state["notes.input_raw"] = st.text_area("Paste note (text/markdown)", value=st.session_state.get("notes.input_raw", ""), height=220)
        st.session_state["notes.prompt"] = st.text_area("Note transform prompt", value=st.session_state.get("notes.prompt", ""), height=110)

        prov = st.selectbox("Provider", PROVIDERS, index=PROVIDERS.index(st.session_state.get("notes.model_provider", "openai")))
        st.session_state["notes.model_provider"] = prov
        model = st.selectbox("Model", SUPPORTED_MODELS.get(prov, []), index=0)
        st.session_state["notes.model"] = model

        max_tokens = st.number_input("max_tokens", min_value=256, max_value=32000, value=6000, step=256)
        temperature = st.slider("temperature", 0.0, 1.0, 0.2, 0.05)

        if st.button("Transform note to organized Markdown"):
            try:
                inp = st.session_state.get("notes.input_raw", "")
                if not inp.strip():
                    st.error("Empty note.")
                else:
                    sys_p = "You are an expert note organizer. Output clean Markdown. Do not invent facts."
                    usr_p = st.session_state.get("notes.prompt", "")
                    out, meta = llm_execute(prov, model, sys_p, usr_p, inp, max_tokens, temperature)
                    meta["kind"] = "note_transform"
                    if not st.session_state.get("notes.output_artifact_id"):
                        aid = create_artifact(out, fmt="markdown", metadata=meta)
                        st.session_state["notes.output_artifact_id"] = aid
                    else:
                        aid = st.session_state["notes.output_artifact_id"]
                        cur, curm = artifact_get_current(aid)
                        artifact_add_version(aid, out, created_by="note_transform", metadata=meta, parent_version_id=curm.get("version_id"))
                    st.session_state["notes.magics.history"].append({"magic": "transform", "ts": now_taipei_str(), "provider": prov, "model": model})
                    safe_event("note_keeper", "info", "Note transformed.")
                    st.success("Transformed.")
            except Exception as e:
                safe_event("note_keeper", "err", f"Note transform failed: {e}")
                st.error(str(e))

    with c2:
        st.markdown("### AI Magics")
        magics = [
            ("AI Formatting", "Rewrite into clearer Markdown structure with consistent headings."),
            ("AI Action Items", "Extract action items with owner and due date if present."),
            ("AI Compliance Checklist", "Generate a compliance checklist derived from the note."),
            ("AI Deficiency Finder", "Find missing information and potential regulatory gaps."),
            ("AI Keywords (Colored)", "Extract key terms and suggest colored keyword palette."),
            # 3 additional WOW AI features for notes (simple variants):
            ("WOW Bullet-to-Brief", "Convert long notes into a 1-page executive brief with key bullets."),
            ("WOW Meeting-to-SOP", "Convert discussion into draft SOP steps (if applicable)."),
            ("WOW Risk Flags", "Flag potential risk statements and categorize severity."),
        ]
        magic = st.selectbox("Select magic", [m[0] for m in magics])
        st.caption(next((m[1] for m in magics if m[0] == magic), ""))

        if st.button("Run Magic"):
            aid = st.session_state.get("notes.output_artifact_id")
            if not aid:
                st.warning("Transform a note first (or create an output artifact).")
            else:
                try:
                    text, curm = artifact_get_current(aid)
                    prov = st.session_state.get("notes.model_provider", "openai")
                    model = st.session_state.get("notes.model", "gpt-4o-mini")
                    sys_p = "You are a helpful assistant. Output Markdown. Do not invent facts."
                    usr_p = f"Magic: {magic}\n\nApply this transformation to the provided note."
                    out, meta = llm_execute(prov, model, sys_p, usr_p, text, 6000, 0.2)
                    artifact_add_version(aid, out, created_by=f"magic:{magic}", metadata={"kind": "note_magic", "magic": magic, **meta}, parent_version_id=curm.get("version_id"))
                    st.session_state["notes.magics.history"].append({"magic": magic, "ts": now_taipei_str(), "provider": prov, "model": model})
                    safe_event("note_keeper", "info", f"Magic executed: {magic}")
                    st.success("Magic applied (new version created).")
                except Exception as e:
                    safe_event("note_keeper", "err", f"Magic failed: {e}")
                    st.error(str(e))

        st.markdown("### Keyword Coloring")
        palette = st.session_state.get("notes.keywords.palette", {})
        if pd is not None:
            dfp = pd.DataFrame([{"keyword": k, "color": v} for k, v in palette.items()])
            edited = st.data_editor(dfp, num_rows="dynamic", use_container_width=True, hide_index=True)
            new_palette = {}
            for _, row in edited.iterrows():
                kw = str(row.get("keyword", "")).strip()
                col = str(row.get("color", "")).strip()
                if kw and col:
                    new_palette[kw] = col
            st.session_state["notes.keywords.palette"] = new_palette
        else:
            st.json(palette)

    st.divider()
    aid = st.session_state.get("notes.output_artifact_id")
    if aid:
        st.markdown("## Note Output")
        tabs = st.tabs(["Text", "Markdown", "Diff", "Versions", "History"])
        text, meta = artifact_get_current(aid)

        with tabs[0]:
            edited = st.text_area("Edit note output", value=text, height=260)
            if st.button("Save note edit"):
                artifact_add_version(aid, edited, created_by="user_edit", metadata={"type": "note_edit"}, parent_version_id=meta.get("version_id"))
                safe_event("note_keeper", "info", "Note edited.")
        with tabs[1]:
            st.markdown(markdown_highlight_keywords(text, st.session_state.get("notes.keywords.palette", {})), unsafe_allow_html=True)
        with tabs[2]:
            versions = artifact_versions(aid)
            if len(versions) >= 2:
                prev = versions[-2]["content_text"]
                st.markdown(simple_diff(prev, text), unsafe_allow_html=True)
            else:
                st.info("Need at least 2 versions for diff.")
        with tabs[3]:
            versions = artifact_versions(aid)
            for v in reversed(versions[-10:]):
                st.write(f"- {v['created_at']} | {v['created_by']} | {v['version_id'][:8]}")
            sel_vid = st.selectbox("Restore version (note)", [v["version_id"] for v in versions][::-1], key="restore_note")
            if st.button("Restore selected (note)"):
                st.session_state["artifacts"][aid]["current_version_id"] = sel_vid
                safe_event("note_keeper", "warn", f"Restored note version {sel_vid[:8]}.")
        with tabs[4]:
            st.json(st.session_state.get("notes.magics.history", []))

        st.download_button("Download note markdown", data=text.encode("utf-8"), file_name="note.md", mime="text/markdown")
    else:
        st.info("No note output yet.")


def render_sidebar_danger_zone():
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"### {t('danger_zone')}")
    st.sidebar.caption(t("purge_confirm"))
    if st.sidebar.button(t("total_purge")):
        total_purge()
        st.rerun()


# -----------------------------
# 13) Main
# -----------------------------
def main():
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    init_state()
    inject_css()

    # Sidebar: keys + purge
    render_key_section()
    render_sidebar_danger_zone()

    render_header()
    render_status_strip()

    if st.session_state.get("ui.mode") == "note_keeper":
        render_note_keeper()
        return

    # Command center split pane
    left, right = st.columns([1.05, 1.25], gap="large")
    with left:
        render_left_pane()
    with right:
        render_agents_and_intelligence()


if __name__ == "__main__":
    main()
