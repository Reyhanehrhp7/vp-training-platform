"""
Virtual Patient Training System - Streamlit Web Interface

A user-friendly web application for clinical communication skills training.
Run with: streamlit run app.py
"""

import streamlit as st
import json
import uuid
import os
from datetime import datetime
from pathlib import Path
try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None
from vp_interaction import VPConversationManager
from vp_feedback import FeedbackGenerator
from vp_cases import CASE_PROFILES, DEFAULT_CASE_KEY
from vp_personalities import PERSONALITY_OVERLAYS
from sp_session_store import load_or_create_session, get_session, append_message, close_session, assign_sp_patient, list_waiting_sessions

def _get_api_key() -> str:
    # Priority: Streamlit secrets -> environment variable.
    try:
        secret_key = st.secrets.get("OPENAI_API_KEY", "")
        if secret_key:
            return str(secret_key).strip()
    except Exception:
        # Local runs may not have a secrets.toml file.
        pass
    return os.getenv("OPENAI_API_KEY", "").strip()


API_KEY = _get_api_key()

# Page configuration
st.set_page_config(
    page_title="Virtual Patient Training",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

if not CASE_PROFILES:
    st.error("No case profiles are configured. Add prompt files to vp_cases before running the app.")
    st.stop()

DEFAULT_CASE = DEFAULT_CASE_KEY or next(iter(CASE_PROFILES))

# Combination schedule (from study table): Group x Slot -> Mode, Case code, Level.
COMBINATION_SCHEDULE = {
    "A1": ("vp", "C1", "L"),
    "A2": ("vp", "C2", "H"),
    "A3": ("vp", "C3", "L"),
    "A4": ("sp", "C1", "H"),
    "A5": ("sp", "C2", "L"),
    "A6": ("sp", "C3", "H"),
    "B1": ("vp", "C1", "H"),
    "B2": ("vp", "C2", "L"),
    "B3": ("vp", "C3", "H"),
    "B4": ("sp", "C1", "L"),
    "B5": ("sp", "C2", "H"),
    "B6": ("sp", "C3", "L"),
    "C1": ("sp", "C1", "L"),
    "C2": ("sp", "C2", "H"),
    "C3": ("sp", "C3", "L"),
    "C4": ("vp", "C1", "H"),
    "C5": ("vp", "C2", "L"),
    "C6": ("vp", "C3", "H"),
    "D1": ("sp", "C1", "H"),
    "D2": ("sp", "C2", "L"),
    "D3": ("sp", "C3", "H"),
    "D4": ("vp", "C1", "L"),
    "D5": ("vp", "C2", "H"),
    "D6": ("vp", "C3", "L"),
}


def _case_code_map() -> dict:
    # Map C1/C2/C3 to preferred case keys if present, otherwise fallback to first 3 configured cases.
    preferred = ["migraine", "tia", "parkinsons"]
    available = list(CASE_PROFILES.keys())
    chosen = [key for key in preferred if key in CASE_PROFILES]
    if len(chosen) < 3:
        for key in available:
            if key not in chosen:
                chosen.append(key)
            if len(chosen) == 3:
                break
    if not chosen:
        chosen = [DEFAULT_CASE]
    while len(chosen) < 3:
        chosen.append(chosen[-1])
    return {"C1": chosen[0], "C2": chosen[1], "C3": chosen[2]}


def _level_to_personality(level_code: str) -> str:
    if level_code == "H":
        return "hard"
    return "easy"


def _build_combo_link(base_url: str, combo_key: str) -> str:
    base = base_url.rstrip("/")
    return f"{base}/?combo={combo_key}"


def _build_doctor_link(base_url: str, combo_key: str) -> str:
    base = base_url.rstrip("/")
    return f"{base}/?combo={combo_key}&participant=doctor"


def _session_id_for_combo(combo_key: str) -> str:
    return f"study_{combo_key.lower()}"


def _build_sp_join_link(base_url: str, session_id: str) -> str:
    base = base_url.rstrip("/")
    return f"{base}/?participant=sp&session={session_id}"


def _default_base_url() -> str:
    # Use deployed URL when available; avoids localhost-only link generation.
    return os.getenv("PUBLIC_BASE_URL", "https://your-app-domain")


def _apply_combo_from_query_params() -> None:
    combo_key = st.query_params.get("combo", "")
    if not combo_key:
        return
    combo_key = str(combo_key).strip().upper()
    assignment = COMBINATION_SCHEDULE.get(combo_key)
    if not assignment:
        st.sidebar.warning(f"Unknown combo '{combo_key}'.")
        return

    mode, case_code, level = assignment
    case_map = _case_code_map()
    mapped_case = case_map.get(case_code)
    if mapped_case not in CASE_PROFILES:
        st.sidebar.warning(f"Case mapping for {case_code} not available.")
        return

    st.session_state.interaction_mode = mode
    st.session_state.platform_role = "doctor"
    st.session_state.selected_case = mapped_case
    st.session_state.selected_personality = _level_to_personality(level)
    if mode == "sp":
        st.session_state.sp_session_id = _session_id_for_combo(combo_key)
    else:
        st.session_state.sp_session_id = ""
    st.session_state.admin_unlocked = False
    st.session_state.assigned_combo = combo_key


def _apply_participant_from_query_params() -> None:
    participant = str(st.query_params.get("participant", "")).strip().lower()
    if participant == "sp":
        st.session_state.interaction_mode = "sp"
        st.session_state.platform_role = "sp_patient"
        st.session_state.admin_unlocked = True
        session_id = str(st.query_params.get("session", "")).strip()
        if session_id:
            st.session_state.sp_session_id = session_id
    elif participant == "doctor":
        st.session_state.platform_role = "doctor"
        st.session_state.admin_unlocked = False

ASSET_BASE_PATH = Path(__file__).resolve().parent / "Stephanie Turner"


def _safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError):
        return ""


PHYSICAL_EXAM_CONTENT = _safe_read_text(ASSET_BASE_PATH / "Physical_exam.txt")
CHEST_XRAY_FILES = [
    path for path in [
        ASSET_BASE_PATH / "chest_x_ray1.jpeg",
        ASSET_BASE_PATH / "chest_x_ray2.jpeg"
    ]
    if path.exists()
]
LUNG_AUDIO_FILE = ASSET_BASE_PATH / "lung_ausculation.mov"
if not LUNG_AUDIO_FILE.exists():
    LUNG_AUDIO_FILE = None

PHYSICAL_EXAM_KEYWORDS = [
    "physical exam",
    "physical examination",
    "exam findings",
    "labs",
    "lab tests",
    "laboratory",
    "blood work"
]
CHEST_XRAY_KEYWORDS = [
    "chest x-ray",
    "chest xray",
    "cxr",
    "chest radiograph",
    "chest imaging"
]
LUNG_SOUND_KEYWORDS = [
    "lung sounds",
    "auscultation",
    "listen to lungs",
    "lung auscultation"
]
GENERAL_TEST_REQUEST_KEYWORDS = [
    "test",
    "exam",
    "results",
    "imaging",
    "ct",
    "mri",
    "ultrasound",
    "scan",
    "labs",
    "laboratory",
    "blood work"
]


def _matches_keywords(message: str, keywords) -> bool:
    text = message.lower()
    return any(keyword in text for keyword in keywords)


def _is_general_test_request(message: str) -> bool:
    return any(keyword in message for keyword in GENERAL_TEST_REQUEST_KEYWORDS)


def _add_clinical_asset(asset_type: str) -> None:
    if "clinical_assets" not in st.session_state:
        st.session_state.clinical_assets = []
    if any(asset["type"] == asset_type for asset in st.session_state.clinical_assets):
        return
    if asset_type == "physical_exam" and PHYSICAL_EXAM_CONTENT:
        st.session_state.clinical_assets.append({
            "type": "physical_exam",
            "title": "Physical Exam & Labs",
            "content": PHYSICAL_EXAM_CONTENT
        })
    elif asset_type == "chest_xray" and CHEST_XRAY_FILES:
        st.session_state.clinical_assets.append({
            "type": "chest_xray",
            "title": "Chest X-ray Imaging",
            "files": [
                {
                    "path": str(path),
                    "caption": path.name.replace("_", " ").replace(".jpeg", "").title()
                }
                for path in CHEST_XRAY_FILES
            ]
        })
    elif asset_type == "lung_audio" and LUNG_AUDIO_FILE:
        st.session_state.clinical_assets.append({
            "type": "lung_audio",
            "title": "Lung Auscultation Audio",
            "file": str(LUNG_AUDIO_FILE)
        })


def _handle_structured_request(user_message: str) -> bool:
    normalized = user_message.lower()
    responses = []
    handled_category = False
    if _matches_keywords(normalized, PHYSICAL_EXAM_KEYWORDS):
        handled_category = True
        if PHYSICAL_EXAM_CONTENT:
            _add_clinical_asset("physical_exam")
            responses.append("Here are the available physical exam findings and labs:\n" + PHYSICAL_EXAM_CONTENT)
        else:
            responses.append("I don't have physical exam data available right now.")
    if _matches_keywords(normalized, CHEST_XRAY_KEYWORDS):
        handled_category = True
        if CHEST_XRAY_FILES:
            _add_clinical_asset("chest_xray")
            image_list = ", ".join(path.name for path in CHEST_XRAY_FILES)
            responses.append(f"Chest X-ray images ({image_list}) are now available under Clinical Data Provided for review.")
        else:
            responses.append("I don't have chest X-ray imaging available right now.")
    if _matches_keywords(normalized, LUNG_SOUND_KEYWORDS):
        handled_category = True
        if LUNG_AUDIO_FILE:
            _add_clinical_asset("lung_audio")
            responses.append("I've added the lung auscultation audio clip for you to listen to in the Clinical Data Provided section.")
        else:
            responses.append("I don't have lung auscultation audio available right now.")
    if not responses and _is_general_test_request(normalized):
        responses.append("I don't have that information right now.")
        handled_category = True
    if responses:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "\n\n".join(responses)
        })
    return bool(responses) or handled_category


def _parse_reasoning_items(raw_text: str) -> list:
    return [line.strip() for line in raw_text.splitlines() if line.strip()]


def _sync_connection_map(connections: dict, findings: list, differentials: list) -> dict:
    if not connections:
        return {}
    synced = {}
    for finding, linked_diffs in connections.items():
        if finding not in findings:
            continue
        valid_diffs = [diff for diff in linked_diffs if diff in differentials]
        if valid_diffs:
            synced[finding] = valid_diffs
    return synced


def _format_sp_display_name(sender_role: str, sender_id: str) -> str:
    if sender_role in {"doctor", "student"}:
        return f"👨‍⚕️ Doctor ({sender_id})"
    if sender_role in {"sp_patient", "sp_actor"}:
        return f"🧑‍⚕️ SP Patient ({sender_id})"
    return sender_id


def _sp_transcript_for_export(messages: list) -> list:
    transcript = []
    for i, msg in enumerate(messages):
        sender_role = msg.get("sender_role", "")
        speaker = "Doctor" if sender_role in {"doctor", "student"} else "SP Patient"
        transcript.append({
            "turn": i + 1,
            "speaker": speaker,
            "role": sender_role,
            "message": msg.get("content", ""),
            "timestamp": msg.get("timestamp")
        })
    return transcript


def _render_clinical_assets() -> None:
    if not st.session_state.clinical_assets:
        st.info("No clinical data requested yet.")
        return

    for asset in st.session_state.clinical_assets:
        if asset["type"] == "physical_exam":
            st.markdown(f"#### {asset['title']}")
            st.write(asset["content"])
        elif asset["type"] == "chest_xray":
            st.markdown(f"#### {asset['title']}")
            files = asset.get("files", [])
            if files:
                cols = st.columns(len(files))
                for col, file_info in zip(cols, files):
                    with col:
                        st.image(file_info["path"], caption=file_info["caption"], use_column_width=True)
        elif asset["type"] == "lung_audio":
            st.markdown(f"#### {asset['title']}")
            st.audio(asset["file"], format="audio/mp4")


def _stage_progress(current_page: str, session_active: bool) -> tuple[int, int]:
    # Setup -> Interview -> Debrief modeled as 3 stages.
    if not session_active:
        return 1, 3
    if current_page in {"Home", "Setup", "Interview"}:
        return 2, 3
    return 3, 3


def _render_debrief(grade: dict, summary_text: str) -> None:
    st.markdown("### Debrief")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Final Grade", grade.get("letter_grade", "N/A"))
    with col2:
        st.metric("Score", f"{grade.get('percentage', 0)}%")
    with col3:
        st.metric("Level", grade.get("level", "Not rated"))

    st.markdown("#### Competency Snapshot")
    competencies = grade.get("competency_scores", {})
    if competencies:
        for competency, score in competencies.items():
            st.markdown(
                f"""
                <div class=\"feedback-box\"><strong>{competency}</strong><br>{score}</div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("No competency breakdown available yet.")

    st.markdown("#### Narrative Feedback")
    st.info(summary_text or "No summary generated yet.")

# Professional custom CSS styling
st.markdown("""
<style>
    /* Design tokens */
    :root {
        --primary: #0b5d5a;
        --primary-strong: #084542;
        --accent: #e77b2f;
        --soft-surface: #f2f7f6;
        --ink: #102321;
        --muted: #5d7371;
        --ok: #1f8a5b;
        --line: #d7e5e3;
    }

    body {
        font-family: "IBM Plex Sans", "Trebuchet MS", "Segoe UI", sans-serif;
    }

    .main-header {
        background:
            radial-gradient(circle at 15% 15%, rgba(255,255,255,0.22) 0%, transparent 35%),
            linear-gradient(140deg, var(--primary) 0%, var(--primary-strong) 100%);
        color: #ffffff;
        padding: 1.6em;
        border-radius: 16px;
        margin-bottom: 1.2em;
        box-shadow: 0 10px 25px rgba(8, 69, 66, 0.22);
    }

    .main-header h1 {
        margin: 0;
        font-size: 2.2em;
        font-weight: 700;
        letter-spacing: 0.2px;
    }

    .main-header p {
        margin: 0.5em 0 0 0;
        font-size: 1.02em;
        opacity: 0.97;
    }

    .journey-pill {
        background: #ffffff;
        border: 1px solid var(--line);
        border-radius: 999px;
        padding: 0.45em 0.95em;
        font-size: 0.9em;
        color: var(--muted);
        margin-right: 0.4em;
    }

    .journey-pill.active {
        background: rgba(11, 93, 90, 0.12);
        border-color: var(--primary);
        color: var(--primary-strong);
        font-weight: 600;
    }

    .encounter-panel {
        background: #ffffff;
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 1em;
        box-shadow: 0 3px 14px rgba(16, 35, 33, 0.06);
    }

    .feedback-box {
        background: linear-gradient(130deg, #eef8f3 0%, #f7fbf9 100%);
        border: 1px solid #cce7d8;
        padding: 1em;
        border-radius: 12px;
        margin: 0.6em 0;
    }

    .user-message {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-strong) 100%);
        color: white;
        padding: 1em;
        border-radius: 12px;
        margin: 0.7em 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.09);
    }

    .patient-message {
        background: linear-gradient(140deg, #f7fbfa 0%, #edf5f4 100%);
        color: var(--ink);
        padding: 1em;
        border-radius: 12px;
        margin: 0.7em 0;
        border-left: 4px solid var(--accent);
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }

    .stButton > button {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-strong) 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.72em 1.2em !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
    }
    
    .stButton > button:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
        transform: translateY(-2px) !important;
    }
    
    .metric-card {
        background: linear-gradient(160deg, #ffffff 0%, #f8fbfb 100%);
        padding: 1.2em;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 2px 10px rgba(0,0,0,0.06);
        border-top: 4px solid var(--primary);
    }

    .section-header {
        color: var(--primary);
        font-size: 1.5em;
        font-weight: 700;
        margin-top: 2em;
        margin-bottom: 1em;
        display: flex;
        align-items: center;
        gap: 0.5em;
    }
    
    .streamlit-expanderHeader {
        background-color: #f6faf9 !important;
        border-radius: 8px !important;
    }

    .footer {
        text-align: center;
        color: var(--muted);
        font-size: 0.9em;
        margin-top: 3em;
        padding-top: 2em;
        border-top: 1px solid var(--line);
    }

    .status-active {
        background-color: #d4edda;
        color: #155724;
        padding: 0.5em 1em;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9em;
    }
    
    .status-inactive {
        background-color: #f8d7da;
        color: #721c24;
        padding: 0.5em 1em;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9em;
    }

    @media (max-width: 900px) {
        .main-header h1 {
            font-size: 1.65em;
        }
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "vp_manager" not in st.session_state:
    st.session_state.vp_manager = None
if "feedback_gen" not in st.session_state:
    st.session_state.feedback_gen = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_active" not in st.session_state:
    st.session_state.session_active = False
if "turn_count" not in st.session_state:
    st.session_state.turn_count = 0
if "session_start_time" not in st.session_state:
    st.session_state.session_start_time = None
if "selected_case" not in st.session_state or st.session_state.selected_case not in CASE_PROFILES:
    st.session_state.selected_case = DEFAULT_CASE
if "selected_personality" not in st.session_state or st.session_state.selected_personality not in PERSONALITY_OVERLAYS:
    st.session_state.selected_personality = "easy"
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "feedback_history" not in st.session_state:
    st.session_state.feedback_history = []
if "session_summary" not in st.session_state:
    st.session_state.session_summary = None
if "overall_grade" not in st.session_state:
    st.session_state.overall_grade = None
if "clinical_assets" not in st.session_state:
    st.session_state.clinical_assets = []
if "clinical_reasoning" not in st.session_state:
    st.session_state.clinical_reasoning = {
        "findings": "",
        "differentials": "",
        "tests": "",
        "treatments": "",
        "summary": "",
        "notes": "",
        "connections": {}
    }
if "interaction_mode" not in st.session_state:
    st.session_state.interaction_mode = "vp"
if "platform_role" not in st.session_state:
    st.session_state.platform_role = "doctor"
if "sp_session_id" not in st.session_state:
    st.session_state.sp_session_id = ""
if "current_page" not in st.session_state:
    st.session_state.current_page = "Home"
if "interview_started" not in st.session_state:
    st.session_state.interview_started = False
if "admin_unlocked" not in st.session_state:
    st.session_state.admin_unlocked = False
if "assigned_combo" not in st.session_state:
    st.session_state.assigned_combo = ""
if "query_assignment_applied" not in st.session_state:
    st.session_state.query_assignment_applied = False

if not st.session_state.query_assignment_applied:
    _apply_combo_from_query_params()
    _apply_participant_from_query_params()
    st.session_state.query_assignment_applied = True


def _prime_interview_start(case_key: str, is_vp_mode: bool) -> None:
    st.session_state.interview_started = True
    if is_vp_mode and not st.session_state.messages:
        chief_complaint = CASE_PROFILES[case_key]["chief_complaint"].strip().strip('"')
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": f"Hello doctor. {chief_complaint}"
            }
        )


def _start_training_session(selected_case: str, selected_personality: str, platform_role: str) -> bool:
    if not st.session_state.user_id:
        st.error("⚠️ Please enter your User ID first")
        return False

    if st.session_state.interaction_mode == "vp" and not API_KEY:
        st.error("⚠️ OPENAI_API_KEY is missing. Add it in environment variables or Streamlit secrets.")
        return False

    if st.session_state.interaction_mode == "sp" and platform_role == "sp_patient" and not st.session_state.sp_session_id:
        st.error("⚠️ Join a waiting doctor session or enter a Session ID")
        return False

    st.session_state.session_active = True

    if st.session_state.interaction_mode == "vp":
        st.session_state.vp_manager = VPConversationManager(
            selected_case,
            selected_personality,
            API_KEY
        )
        st.session_state.feedback_gen = FeedbackGenerator(API_KEY)
    else:
        st.session_state.vp_manager = None
        st.session_state.feedback_gen = None
        if platform_role == "doctor" and not st.session_state.sp_session_id:
            st.session_state.sp_session_id = f"sp_{selected_case}_{uuid.uuid4().hex[:8]}"
        if platform_role == "sp_patient" and st.session_state.sp_session_id:
            try:
                assign_sp_patient(st.session_state.sp_session_id, st.session_state.user_id)
            except Exception:
                pass
        load_or_create_session(
            session_id=st.session_state.sp_session_id,
            case_key=selected_case,
            case_name=CASE_PROFILES[selected_case]["case_name"],
            doctor_id=st.session_state.user_id if platform_role == "doctor" else None,
            sp_patient_id=st.session_state.user_id if platform_role == "sp_patient" else None,
        )

    st.session_state.messages = []
    st.session_state.turn_count = 0
    st.session_state.session_start_time = datetime.now()
    st.session_state.feedback_history = []
    st.session_state.session_summary = None
    st.session_state.overall_grade = None
    st.session_state.clinical_assets = []
    st.session_state.clinical_reasoning = {
        "findings": "",
        "differentials": "",
        "tests": "",
        "treatments": "",
        "summary": "",
        "notes": "",
        "connections": {}
    }
    st.session_state.interview_started = False
    # Re-lock coordinator controls once a doctor encounter starts.
    if platform_role == "doctor":
        st.session_state.admin_unlocked = False
    return True

# Sidebar configuration
st.sidebar.markdown("## ⚙️ Settings")

ADMIN_PASSCODE = os.getenv("COORDINATOR_PASSCODE", "study-admin")
with st.sidebar.expander("Coordinator Access", expanded=False):
    if st.session_state.admin_unlocked:
        st.success("Coordinator controls unlocked")
        if st.button("Lock Coordinator Controls", key="lock_coordinator_controls"):
            st.session_state.admin_unlocked = False
            st.rerun()
    else:
        coordinator_code = st.text_input("Coordinator code", type="password", key="coordinator_code_input")
        if st.button("Unlock Coordinator Controls", key="unlock_coordinator_controls"):
            if coordinator_code == ADMIN_PASSCODE:
                st.session_state.admin_unlocked = True
                st.rerun()
            else:
                st.error("Invalid coordinator code")

with st.sidebar.expander("Combination Links", expanded=False):
    link_base_url = st.text_input("Base URL", value=_default_base_url(), key="combo_base_url")
    st.caption("Arrange by Group + Slot, then share links directly.")

    coord_col1, coord_col2 = st.columns(2)
    with coord_col1:
        selected_group = st.selectbox("Group", ["A", "B", "C", "D"], key="planner_group")
    with coord_col2:
        selected_slot = st.selectbox("Slot", [1, 2, 3, 4, 5, 6], key="planner_slot")

    planner_combo = f"{selected_group}{selected_slot}"
    assignment = COMBINATION_SCHEDULE.get(planner_combo)
    if assignment:
        planner_mode, planner_case, planner_level = assignment
        st.caption(f"Assignment: {planner_mode.upper()} {planner_case} {planner_level}")
        doctor_link = _build_doctor_link(link_base_url, planner_combo)
        st.text_input("Doctor Link", value=doctor_link, key="planner_doctor_link")
        if planner_mode == "sp":
            planner_session_id = _session_id_for_combo(planner_combo)
            sp_link = _build_sp_join_link(link_base_url, planner_session_id)
            st.text_input("SP Link", value=sp_link, key="planner_sp_link")

    if st.button("Generate Full Schedule Links", key="generate_combo_links", use_container_width=True):
        all_links = []
        for group in ["A", "B", "C", "D"]:
            for slot in range(1, 7):
                combo = f"{group}{slot}"
                mode, case_code, level = COMBINATION_SCHEDULE[combo]
                doctor_link = _build_doctor_link(link_base_url, combo)
                if mode == "sp":
                    session_id = _session_id_for_combo(combo)
                    sp_link = _build_sp_join_link(link_base_url, session_id)
                    all_links.append(f"{combo} ({mode.upper()} {case_code} {level}) | Doctor: {doctor_link} | SP: {sp_link}")
                else:
                    all_links.append(f"{combo} ({mode.upper()} {case_code} {level}) | Doctor: {doctor_link}")
        st.text_area("Shareable Links", value="\n".join(all_links), height=240)

    if (
        st.session_state.interaction_mode == "sp"
        and st.session_state.platform_role == "doctor"
        and st.session_state.sp_session_id
    ):
        sp_join_link = _build_sp_join_link(link_base_url, st.session_state.sp_session_id)
        st.caption("SP Join Link for current session")
        st.text_input("SP Join URL", value=sp_join_link, key="sp_join_url_display")

if st.session_state.assigned_combo:
    st.sidebar.caption(f"Assigned combination: {st.session_state.assigned_combo}")

doctor_blinded_view = st.session_state.platform_role == "doctor" and not st.session_state.admin_unlocked
platform_role = st.session_state.platform_role

if not doctor_blinded_view:
    st.sidebar.markdown("### 🔀 Interaction Mode")
    mode_options = {
        "VP (AI Patient)": "vp",
        "SP (Human Standardized Patient)": "sp"
    }
    selected_mode_label = st.sidebar.radio(
        "Select interview mode:",
        options=list(mode_options.keys()),
        index=0 if st.session_state.interaction_mode == "vp" else 1
    )
    st.session_state.interaction_mode = mode_options[selected_mode_label]

    if st.session_state.interaction_mode == "sp":
        st.sidebar.markdown("### 👥 Platform Role")
        role_options = {
            "Doctor (User)": "doctor",
            "SP Patient (Human)": "sp_patient"
        }
        selected_role_label = st.sidebar.radio(
            "Log in as:",
            options=list(role_options.keys()),
            index=0 if st.session_state.platform_role == "doctor" else 1
        )
        platform_role = role_options[selected_role_label]
        st.session_state.platform_role = platform_role
    else:
        st.session_state.platform_role = "doctor"
        platform_role = "doctor"
else:
    st.sidebar.caption("Blinded participant view enabled.")
    st.session_state.platform_role = "doctor"
    platform_role = "doctor"

# User ID input
st.sidebar.markdown("### 👤 User Information")
user_id = st.sidebar.text_input(
    "Doctor/User ID" if platform_role == "doctor" else "SP Patient ID",
    placeholder="e.g., S123456 or student@university.edu",
    help="Unique ID for this user"
)
if user_id:
    st.session_state.user_id = user_id
else:
    st.session_state.user_id = None

# Case selection
st.sidebar.markdown("### 📋 Clinical Case")
case_options = list(CASE_PROFILES.keys())
selected_case = st.sidebar.selectbox(
    "Select case:",
    case_options,
    format_func=lambda x: f"🏥 {x.upper()} - {CASE_PROFILES[x]['case_name']}",
    key="case_select"
)
st.session_state.selected_case = selected_case

personality_options = list(PERSONALITY_OVERLAYS.keys())
personality_icons = {
    "easy": "🙂",
    "medium": "😟",
    "hard": "😰"
}

if st.session_state.interaction_mode == "vp":
    if doctor_blinded_view:
        selected_personality = st.session_state.selected_personality
    else:
        st.sidebar.markdown("### 😊 Patient Personality")
        selected_personality = st.sidebar.selectbox(
            "Select personality:",
            personality_options,
            format_func=lambda x: f"{personality_icons.get(x, '')} {x.capitalize()}",
            key="personality_select"
        )
else:
    selected_personality = st.session_state.selected_personality
st.session_state.selected_personality = selected_personality

if st.session_state.interaction_mode == "sp" and not doctor_blinded_view:
    st.sidebar.markdown("### 🔑 SP Live Session")
    if platform_role == "doctor":
        st.sidebar.caption("Step 1: Enter Doctor ID. Step 2: Click Start to create a waiting session.")
        sp_session_id = st.sidebar.text_input(
            "Session ID (optional)",
            value=st.session_state.sp_session_id,
            placeholder="Leave blank to auto-create",
            help="If blank, a unique session ID is generated when you click Start"
        )
        st.session_state.sp_session_id = sp_session_id.strip()
        st.sidebar.caption("After Start, this session appears in the SP waiting list.")
    else:
        st.sidebar.caption("Step 1: Enter SP Patient ID. Step 2: Join a waiting doctor session.")
        waiting_sessions = list_waiting_sessions()
        if waiting_sessions:
            session_labels = {
                s["session_id"]: f"{s['case_name']} | Doctor: {s['doctor_id']} | Session: {s['session_id']}"
                for s in waiting_sessions
            }
            selected_waiting_session_id = st.sidebar.selectbox(
                "Available doctor sessions",
                options=list(session_labels.keys()),
                format_func=lambda session_id: session_labels[session_id],
                key="sp_waiting_select"
            )
            if st.sidebar.button("🤝 Join & Start Session", use_container_width=True):
                if not st.session_state.user_id:
                    st.sidebar.error("Enter your SP Patient ID first")
                else:
                    joined = assign_sp_patient(selected_waiting_session_id, st.session_state.user_id)
                    st.session_state.sp_session_id = selected_waiting_session_id
                    joined_case = joined.get("metadata", {}).get("case")
                    if joined_case in CASE_PROFILES:
                        st.session_state.selected_case = joined_case
                    st.sidebar.success(f"Joined session: {selected_waiting_session_id}")
                    if _start_training_session(st.session_state.selected_case, selected_personality, platform_role):
                        st.rerun()
        else:
            st.sidebar.info("No waiting doctor sessions yet.")

        sp_session_id = st.sidebar.text_input(
            "Or enter Session ID manually",
            value=st.session_state.sp_session_id,
            placeholder="e.g., chestpain_2pm_groupA",
            help="Use this only if you already know the session ID"
        )
        st.session_state.sp_session_id = sp_session_id.strip()

# Display case details
st.sidebar.markdown("### 📝 Patient Profile")
with st.sidebar.expander("View Profile"):
    case_data = CASE_PROFILES[selected_case]
    st.markdown(f"**Case:** {case_data['case_name']}")
    st.markdown(f"**Chief Complaint:** \"{case_data['chief_complaint']}\"")
    st.markdown("**Profile:**")
    st.markdown(case_data['case_prompt'])

# Page options (rendered in main header navigation)
available_pages = ["Home", "Setup", "Interview", "Reasoning", "Session Actions"]

if st.session_state.current_page not in available_pages:
    st.session_state.current_page = available_pages[0]

# Session controls
st.sidebar.markdown("### 🎮 Controls")
col1, col2 = st.sidebar.columns(2)
if doctor_blinded_view:
    start_label = "▶️ Start Encounter"
else:
    start_label = "▶️ Create Session" if st.session_state.interaction_mode == "sp" and platform_role == "doctor" else "▶️ Start"

with col1:
    if st.button(start_label, use_container_width=True):
        if _start_training_session(selected_case, selected_personality, platform_role):
            st.rerun()

with col2:
    if st.button("🔄 Reset", use_container_width=True):
        st.session_state.messages = []
        st.session_state.turn_count = 0
        st.session_state.interview_started = False
        if st.session_state.interaction_mode == "vp" and st.session_state.vp_manager:
            st.session_state.vp_manager.reset_conversation()
        st.session_state.clinical_assets = []
        st.session_state.clinical_reasoning = {
            "findings": "",
            "differentials": "",
            "tests": "",
            "treatments": "",
            "summary": "",
            "notes": "",
            "connections": {}
        }
        st.rerun()

if st.sidebar.button("⏹️ End", use_container_width=True):
    # Auto-save session before ending
    if st.session_state.session_active:
        try:
            if st.session_state.interaction_mode == "vp" and st.session_state.vp_manager:
                # Generate session summary and grade if not already generated
                if not st.session_state.session_summary:
                    with st.spinner("📊 Generating final assessment..."):
                        summary_result = st.session_state.feedback_gen.generate_session_summary_feedback(
                            case_name=st.session_state.vp_manager.case_name,
                            personality=st.session_state.selected_personality,
                            conversation_history=st.session_state.vp_manager.get_conversation_history()
                        )
                        st.session_state.session_summary = summary_result.get("session_feedback", "")
                        st.session_state.overall_grade = {
                            "letter_grade": summary_result.get("overall_grade", {}).get("letter_grade", "N/A"),
                            "percentage": summary_result.get("overall_grade", {}).get("percentage", 0),
                            "level": summary_result.get("overall_grade", {}).get("level", "Not rated"),
                            "competency_scores": summary_result.get("overall_grade", {}).get("competency_scores", {})
                        }
            
            # Create user data directory
            user_dir = Path("data") / st.session_state.user_id
            user_dir.mkdir(parents=True, exist_ok=True)
            if st.session_state.interaction_mode == "vp" and st.session_state.vp_manager:
                transcript = [
                    {
                        "turn": i + 1,
                        "speaker": "Clinician" if msg["role"] == "user" else "Patient",
                        "role": msg["role"],
                        "message": msg["content"]
                    }
                    for i, msg in enumerate(st.session_state.vp_manager.get_conversation_history())
                ]
                case_name = st.session_state.vp_manager.case_name
                session_data = {
                    "user_id": st.session_state.user_id,
                    "session_metadata": {
                        "mode": "vp",
                        "case": st.session_state.selected_case,
                        "case_name": case_name,
                        "personality": st.session_state.selected_personality,
                        "total_turns": st.session_state.turn_count,
                        "session_start": st.session_state.session_start_time.isoformat(),
                        "session_end": datetime.now().isoformat()
                    },
                    "case_details": CASE_PROFILES[st.session_state.selected_case],
                    "personality_details": PERSONALITY_OVERLAYS[st.session_state.selected_personality],
                    "transcript": transcript,
                    "feedback_data": st.session_state.feedback_history,
                    "session_summary": st.session_state.session_summary,
                    "overall_grade": st.session_state.overall_grade,
                    "clinical_reasoning": st.session_state.clinical_reasoning
                }
                filename = f"session_{st.session_state.selected_case}_{st.session_state.selected_personality}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            else:
                live_session = get_session(st.session_state.sp_session_id)
                live_messages = live_session.get("messages", [])
                session_data = {
                    "user_id": st.session_state.user_id,
                    "session_metadata": {
                        "mode": "sp",
                        "role": st.session_state.platform_role,
                        "sp_session_id": st.session_state.sp_session_id,
                        "case": st.session_state.selected_case,
                        "case_name": CASE_PROFILES[st.session_state.selected_case]["case_name"],
                        "total_turns": len(live_messages),
                        "session_start": st.session_state.session_start_time.isoformat(),
                        "session_end": datetime.now().isoformat()
                    },
                    "case_details": CASE_PROFILES[st.session_state.selected_case],
                    "transcript": _sp_transcript_for_export(live_messages),
                    "clinical_reasoning": st.session_state.clinical_reasoning
                }
                if doctor_blinded_view:
                    filename = f"session_{st.session_state.selected_case}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                else:
                    filename = f"session_sp_{st.session_state.selected_case}_{st.session_state.sp_session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = user_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(session_data, f, indent=2)

            if st.session_state.interaction_mode == "sp" and st.session_state.sp_session_id:
                close_session(st.session_state.sp_session_id)
            
            # Display relative path for success message
            relative_path = f"data/{st.session_state.user_id}/{filename}"
            if doctor_blinded_view:
                st.success("✅ Session saved successfully.")
            else:
                st.success(f"✅ Session saved: {relative_path}")
            if st.session_state.interaction_mode == "vp":
                # Display overall feedback and scores
                st.divider()
                _render_debrief(st.session_state.overall_grade, st.session_state.session_summary)
                st.divider()
                st.markdown("✅ **Session successfully saved and analyzed!**")
            else:
                if doctor_blinded_view:
                    st.info("Session closed and transcript saved.")
                else:
                    st.info("SP live session closed and transcript saved.")
            
        except Exception as e:
            st.error(f"❌ Error saving session: {str(e)}")
    
    st.session_state.session_active = False
    st.session_state.vp_manager = None
    st.session_state.interview_started = False

# Main content
st.markdown("""
<div class="main-header">
    <h1>🏥 Virtual Patient Training</h1>
    <p>Structured encounter workflow with interview, reasoning, and debrief tools</p>
</div>
""", unsafe_allow_html=True)

stage_now, stage_total = _stage_progress(st.session_state.current_page, st.session_state.session_active)
st.progress(stage_now / stage_total)
st.markdown(
    f"""
    <span class=\"journey-pill {'active' if stage_now == 1 else ''}\">1. Setup</span>
    <span class=\"journey-pill {'active' if stage_now == 2 else ''}\">2. Interview</span>
    <span class=\"journey-pill {'active' if stage_now == 3 else ''}\">3. Debrief</span>
    """,
    unsafe_allow_html=True
)

st.markdown("### 🧭 Navigation")
nav_cols = st.columns(5)
for idx, page_name in enumerate(available_pages):
    with nav_cols[idx]:
        button_label = f"• {page_name}" if st.session_state.current_page == page_name else page_name
        if st.button(button_label, key=f"nav_{page_name}", use_container_width=True):
            st.session_state.current_page = page_name
            st.rerun()

if not st.session_state.session_active:
    if st.session_state.current_page == "Setup":
        st.markdown("### ⚙️ Setup")
        st.info("Confirm your user ID and case from the sidebar, then click Start Encounter.")
        st.markdown(f"**Selected case:** {CASE_PROFILES[selected_case]['case_name']}")
        if st.session_state.interaction_mode == "vp" and not doctor_blinded_view:
            st.markdown(f"**VP personality:** {selected_personality}")
        if st.session_state.interaction_mode == "sp" and not doctor_blinded_view:
            active_session_id = st.session_state.sp_session_id or "(will auto-generate for doctor)"
            st.markdown(f"**SP session ID:** {active_session_id}")
    elif st.session_state.current_page == "Interview":
        st.markdown("### Interview")
        st.info("Start directly from here, then the chat will open immediately.")
        start_here_label = "▶ Start Interview with Patient"
        if st.button(start_here_label, key="start_interview_from_empty_page", use_container_width=True):
            if _start_training_session(selected_case, selected_personality, platform_role):
                _prime_interview_start(selected_case, st.session_state.interaction_mode == "vp")
                st.session_state.current_page = "Interview"
                st.rerun()
        st.caption("You can also start from the sidebar controls.")
    elif st.session_state.current_page in {"Reasoning", "Session Actions"}:
        st.markdown(f"### {st.session_state.current_page}")
        st.info("Start a session first, then this page will become active.")
        st.markdown("Use **Setup** page, **Interview** page button, or sidebar controls to start.")
    else:
        # Welcome screen
        col1, col2 = st.columns(2)

        with col1:
            case_count = len(CASE_PROFILES)
            case_label = "Case" if case_count == 1 else "Cases"
            case_names = ", ".join(case["case_name"] for case in CASE_PROFILES.values())
            st.markdown(f"""
            ### 🎯 System Features

            - **📚 {case_count} Clinical {case_label}**: {case_names}
            - **🧑‍⚕️ Standardized Encounter Flow**: Consistent interview experience
            - **💬 Unified Chat Interface**: Same clinician workflow across encounters
            - **📋 Real-time Feedback**: Immediate evaluation of communication
            - **💾 Session Export**: Save and review practice sessions
            """)

        with col2:
            st.markdown("""
            ### 📖 How to Use

            1. **Enter User ID** - Use your clinician identifier
            2. **Select Case** - Choose a clinical scenario
            3. **Start Encounter** - Begin the interview
            4. **Communicate** - Interview and capture reasoning notes
            5. **Debrief** - Review feedback and scores
            6. **Export** - Save your session for review
            """)

        st.markdown("---")

else:
    is_vp_mode = st.session_state.interaction_mode == "vp"
    if is_vp_mode and not st.session_state.vp_manager:
        st.error("❌ Error initializing encounter session")
    else:
        live_session = None
        live_messages = []
        if not is_vp_mode:
            live_session = get_session(st.session_state.sp_session_id)
            live_messages = live_session.get("messages", [])
            st.session_state.turn_count = len(live_messages)

        # Session metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 2em; color: #0066cc;">🏥</div>
                <div style="font-size: 0.9em; color: #666; margin-top: 0.5em;">{selected_case.upper()}</div>
                <div style="font-size: 1.2em; font-weight: bold; color: #212529;">{CASE_PROFILES[selected_case]['case_name']}</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            if doctor_blinded_view:
                st.markdown("""
                <div class="metric-card">
                    <div style="font-size: 2em; color: #0066cc;">🩺</div>
                    <div style="font-size: 0.9em; color: #666; margin-top: 0.5em;">Patient Status</div>
                    <div style="font-size: 1.2em; font-weight: bold; color: #212529;">Assigned</div>
                </div>
                """, unsafe_allow_html=True)
            elif is_vp_mode:
                st.markdown(f"""
                <div class="metric-card">
                    <div style="font-size: 2em; color: #0066cc;">{personality_icons.get(selected_personality, '')}</div>
                    <div style="font-size: 0.9em; color: #666; margin-top: 0.5em;">Personality</div>
                    <div style="font-size: 1.2em; font-weight: bold; color: #212529;">{selected_personality.capitalize()}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="metric-card">
                    <div style="font-size: 2em; color: #0066cc;">🆔</div>
                    <div style="font-size: 0.9em; color: #666; margin-top: 0.5em;">Session ID</div>
                    <div style="font-size: 1.2em; font-weight: bold; color: #212529;">{st.session_state.sp_session_id}</div>
                </div>
                """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 2em; color: #00a86b;">💬</div>
                <div style="font-size: 0.9em; color: #666; margin-top: 0.5em;">Messages</div>
                <div style="font-size: 1.2em; font-weight: bold; color: #212529;">{st.session_state.turn_count}</div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            elapsed = ""
            if st.session_state.session_start_time:
                elapsed_time = datetime.now() - st.session_state.session_start_time
                minutes = int(elapsed_time.total_seconds() / 60)
                seconds = int(elapsed_time.total_seconds() % 60)
                elapsed = f"{minutes}:{seconds:02d}"

            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 2em; color: #0066cc;">⏱️</div>
                <div style="font-size: 0.9em; color: #666; margin-top: 0.5em;">Time</div>
                <div style="font-size: 1.2em; font-weight: bold; color: #212529;">{elapsed}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        active_page = st.session_state.current_page
        if active_page == "Home":
            st.markdown("### 🏠 Session Home")
            st.info("Use sidebar Pages to open Interview, Reasoning, or Session Actions.")
            if is_vp_mode or doctor_blinded_view:
                preview_messages = st.session_state.messages[-3:]
                if preview_messages:
                    st.markdown("#### Recent Conversation")
                    for msg in preview_messages:
                        speaker = "You" if msg["role"] == "user" else "Patient"
                        st.write(f"**{speaker}:** {msg['content']}")
                else:
                    st.write("No messages yet. Open Interview page to begin.")
            else:
                status = live_session.get("status", "active") if live_session else "active"
                st.write(f"**SP session status:** {status}")
                st.write(f"**SP session ID:** {st.session_state.sp_session_id}")
                st.write(f"**Messages so far:** {len(live_messages)}")
                st.write("Open Interview page to chat.")

        if active_page == "Interview":
            st.markdown("### 💬 Interview")

            if not st.session_state.interview_started:
                start_interview_label = "▶ Start Interview with Patient"
                if st.button(start_interview_label, key="start_interview_btn", use_container_width=True):
                    _prime_interview_start(selected_case, is_vp_mode)
                    st.rerun()
                st.info("Press Start Interview to begin the conversation.")
            else:
                st.success("Interview started. You can now continue the conversation.")

            interview_col, tools_col = st.columns([2.1, 1], gap="large")

            with interview_col:
                st.markdown("<div class='encounter-panel'>", unsafe_allow_html=True)
                st.markdown("#### Encounter Transcript")
                if is_vp_mode:
                    for i, msg in enumerate(st.session_state.messages):
                        if msg["role"] == "user":
                            st.markdown(f"""
                            <div class="user-message">
                                <strong>👨‍⚕️ You:</strong><br>
                                {msg['content']}
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div class="patient-message">
                                <strong>🩺 Patient:</strong><br>
                                {msg['content']}
                            </div>
                            """, unsafe_allow_html=True)

                        if i > 0 and msg["role"] == "assistant" and "feedback" in msg:
                            with st.expander("Turn Feedback"):
                                st.markdown(msg["feedback"])
                else:
                    status = live_session.get("status", "active") if live_session else "active"
                    if not doctor_blinded_view:
                        st.caption(f"Mode: SP (Human) | Role: {st.session_state.platform_role} | Live session status: {status}")
                    else:
                        st.caption("Live session status: active")
                    if live_session:
                        metadata = live_session.get("metadata", {})
                        doctor_joined = "Yes" if metadata.get("doctor_id") else "No"
                        sp_joined = "Yes" if metadata.get("sp_patient_id") else "No"
                        if not doctor_blinded_view:
                            st.caption(f"Pairing status: Doctor joined {doctor_joined} | SP patient joined {sp_joined}")
                        if not metadata.get("doctor_id") and st.session_state.platform_role == "sp_patient":
                            st.warning("Waiting for a doctor to create or join this session.")
                        if not metadata.get("sp_patient_id") and st.session_state.platform_role == "doctor" and not doctor_blinded_view:
                            st.info("Session is live. Waiting for an SP patient to join from the waiting list.")
                        if metadata.get("doctor_id") and metadata.get("sp_patient_id"):
                            st.success("Both participants are connected. You can start chatting.")

                    auto_refresh_enabled = st.toggle("Auto-refresh", value=True, key="sp_auto_refresh_toggle")
                    if auto_refresh_enabled and st_autorefresh:
                        st_autorefresh(
                            interval=3000,
                            key=f"sp_autorefresh_{st.session_state.sp_session_id}_{st.session_state.platform_role}"
                        )
                    refresh_col1, refresh_col2 = st.columns([1, 4])
                    with refresh_col1:
                        if st.button("Refresh", key="sp_refresh_btn"):
                            st.rerun()
                    with refresh_col2:
                        if auto_refresh_enabled and st_autorefresh:
                            st.caption("Auto-refreshing every 3 seconds.")
                        elif auto_refresh_enabled and not st_autorefresh:
                            st.caption("Install streamlit-autorefresh for auto polling.")
                        else:
                            st.caption("Manual refresh is active.")

                    for msg in live_messages:
                        sender_role = msg.get("sender_role", "")
                        sender_id = msg.get("sender_id", "unknown")
                        content = msg.get("content", "")
                        display_name = "👨‍⚕️ You" if sender_id == st.session_state.user_id else "🩺 Patient"
                        if not doctor_blinded_view:
                            display_name = _format_sp_display_name(sender_role, sender_id)
                        is_me = sender_id == st.session_state.user_id
                        if is_me:
                            st.markdown(f"""
                            <div class="user-message">
                                <strong>{display_name}:</strong><br>
                                {content}
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div class="patient-message">
                                <strong>{display_name}:</strong><br>
                                {content}
                            </div>
                            """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

            with tools_col:
                st.markdown("<div class='encounter-panel'>", unsafe_allow_html=True)
                st.markdown("#### Encounter Tools")
                st.caption("Use these quick actions during the interview.")
                st.markdown(
                    f"**Case:** {CASE_PROFILES[selected_case]['case_name']}  \\\n+**Chief complaint:** {CASE_PROFILES[selected_case]['chief_complaint']}"
                )
                if is_vp_mode and not doctor_blinded_view:
                    st.markdown(f"**Patient style:** {selected_personality.capitalize()}")
                st.markdown("##### Prompt Starters")
                st.write("- `What worries you most about this today?`")
                st.write("- `Can you describe how this started and changed over time?`")
                st.write("- `What were you hoping we could accomplish in this visit?`")

                if is_vp_mode:
                    st.markdown("##### Clinical Data")
                    _render_clinical_assets()

                if is_vp_mode and st.session_state.feedback_history:
                    latest_feedback = st.session_state.feedback_history[-1]
                    st.markdown("##### Latest Coaching")
                    st.markdown(
                        f"""
                        <div class=\"feedback-box\">
                            <strong>Turn {latest_feedback['turn']}</strong><br>
                            {latest_feedback['feedback'][:280]}...
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                st.markdown("</div>", unsafe_allow_html=True)

        if active_page == "Reasoning":
            st.markdown("### 🧠 Clinical Reasoning Workspace")
            reasoning_tabs = st.tabs(["Clinical Reasoning", "My notes"])
            with reasoning_tabs[0]:
                top_cols = st.columns(2)
                with top_cols[0]:
                    findings_input = st.text_area(
                        "Relevant Findings",
                        value=st.session_state.clinical_reasoning.get("findings", ""),
                        placeholder="Add finding ..."
                    )
                    st.session_state.clinical_reasoning["findings"] = findings_input
                with top_cols[1]:
                    diff_input = st.text_area(
                        "Differentials",
                        value=st.session_state.clinical_reasoning.get("differentials", ""),
                        placeholder="Add differential ..."
                    )
                    st.session_state.clinical_reasoning["differentials"] = diff_input
                mid_cols = st.columns(2)
                with mid_cols[0]:
                    tests_input = st.text_area(
                        "Test/Examination",
                        value=st.session_state.clinical_reasoning.get("tests", ""),
                        placeholder="Add test ..."
                    )
                    st.session_state.clinical_reasoning["tests"] = tests_input
                with mid_cols[1]:
                    treatment_input = st.text_area(
                        "Treatment",
                        value=st.session_state.clinical_reasoning.get("treatments", ""),
                        placeholder="Add treatment ..."
                    )
                    st.session_state.clinical_reasoning["treatments"] = treatment_input
                summary_input = st.text_area(
                    "Summary Statement",
                    value=st.session_state.clinical_reasoning.get("summary", ""),
                    placeholder="Compose a short summary statement about the patient."
                )
                st.session_state.clinical_reasoning["summary"] = summary_input

                findings_list = _parse_reasoning_items(findings_input)
                differentials_list = _parse_reasoning_items(diff_input)
                st.session_state.clinical_reasoning["connections"] = _sync_connection_map(
                    st.session_state.clinical_reasoning.get("connections", {}),
                    findings_list,
                    differentials_list
                )
                connections_map = st.session_state.clinical_reasoning["connections"]

                st.markdown("#### 🔗 Connect Findings to Differentials")
                st.caption("Link the most important findings to the differentials they support.")
                if findings_list and differentials_list:
                    builder_cols = st.columns([3, 3, 1])
                    with builder_cols[0]:
                        selected_finding = st.selectbox(
                            "Finding",
                            options=findings_list,
                            key="connection_finding_select"
                        )
                    with builder_cols[1]:
                        selected_differential = st.selectbox(
                            "Differential",
                            options=differentials_list,
                            key="connection_differential_select"
                        )
                    with builder_cols[2]:
                        if st.button("Link", use_container_width=True, key="add_connection_btn"):
                            links = st.session_state.clinical_reasoning["connections"]
                            linked = links.setdefault(selected_finding, [])
                            if selected_differential not in linked:
                                linked.append(selected_differential)
                                st.session_state.clinical_reasoning["connections"] = links
                else:
                    st.info("Add at least one finding and one differential to start building connections.")

                if connections_map:
                    st.markdown("##### Active Connections")
                    for idx, (finding, linked_diffs) in enumerate(list(connections_map.items())):
                        row_cols = st.columns([4, 5, 1])
                        with row_cols[0]:
                            st.markdown(f"**{finding}**")
                        with row_cols[1]:
                            st.write(", ".join(linked_diffs))
                        with row_cols[2]:
                            if st.button("Remove", key=f"remove_conn_{idx}", use_container_width=True):
                                connections_map.pop(finding, None)
                                st.session_state.clinical_reasoning["connections"] = connections_map
                                st.rerun()
                else:
                    st.info("No connections added yet.")
            with reasoning_tabs[1]:
                notes_input = st.text_area(
                    "My Notes",
                    value=st.session_state.clinical_reasoning.get("notes", ""),
                    placeholder="Capture any additional thoughts or follow-ups."
                )
                st.session_state.clinical_reasoning["notes"] = notes_input

        if active_page == "Interview":
            st.markdown("### ✍️ Your Response")
            input_placeholder = "Type your clinical question or observation..." if is_vp_mode else "Type your message to the other participant..."
            user_input = None
            if st.session_state.interview_started:
                user_input = st.chat_input(input_placeholder)
            else:
                st.caption("Start the interview first to unlock the chat input.")

            if user_input:
                try:
                    if is_vp_mode:
                        st.session_state.messages.append({
                            "role": "user",
                            "content": user_input
                        })
                        st.session_state.turn_count += 1
                        if _handle_structured_request(user_input):
                            st.rerun()

                        with st.spinner("🤔 Patient is responding..."):
                            vp_response = st.session_state.vp_manager.get_vp_response(user_input)

                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": vp_response
                        })

                        with st.spinner("📊 Generating feedback..."):
                            feedback = st.session_state.feedback_gen.generate_turn_feedback(
                                case_name=st.session_state.vp_manager.case_name,
                                personality=selected_personality,
                                learner_utterance=user_input,
                                vp_response=vp_response,
                                turn_number=st.session_state.turn_count
                            )
                            if st.session_state.messages:
                                st.session_state.messages[-1]["feedback"] = feedback["feedback"]
                            st.session_state.feedback_history.append({
                                "turn": st.session_state.turn_count,
                                "clinician_message": user_input,
                                "feedback": feedback["feedback"]
                            })
                    else:
                        append_message(
                            session_id=st.session_state.sp_session_id,
                            sender_role=st.session_state.platform_role,
                            sender_id=st.session_state.user_id,
                            content=user_input,
                        )

                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

        if active_page == "Session Actions":
            st.markdown("---")
            st.markdown("### 📊 Session Actions")

        if active_page == "Session Actions" and is_vp_mode:
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("📋 Session Summary", use_container_width=True):
                    with st.spinner("🔍 Analyzing session..."):
                        try:
                            summary = st.session_state.feedback_gen.generate_session_summary_feedback(
                                case_name=st.session_state.vp_manager.case_name,
                                personality=selected_personality,
                                conversation_history=st.session_state.vp_manager.get_conversation_history()
                            )
                            st.session_state.session_summary = summary.get("session_feedback", "")
                            st.session_state.overall_grade = {
                                "letter_grade": summary.get("overall_grade", {}).get("letter_grade", "N/A"),
                                "percentage": summary.get("overall_grade", {}).get("percentage", 0),
                                "level": summary.get("overall_grade", {}).get("level", "Not rated"),
                                "competency_scores": summary.get("overall_grade", {}).get("competency_scores", {})
                            }

                            _render_debrief(st.session_state.overall_grade, st.session_state.session_summary)
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")

            with col2:
                if st.button("💾 Submit", use_container_width=True):
                    try:
                        session_data = {
                            "session_metadata": {
                                "mode": "vp",
                                "case": selected_case,
                                "case_name": st.session_state.vp_manager.case_name,
                                "personality": selected_personality,
                                "total_turns": st.session_state.turn_count,
                                "session_start": st.session_state.session_start_time.isoformat(),
                                "session_end": datetime.now().isoformat()
                            },
                            "case_details": CASE_PROFILES[selected_case],
                            "personality_details": PERSONALITY_OVERLAYS[selected_personality],
                            "transcript": [
                                {
                                    "turn": i + 1,
                                    "speaker": "Clinician" if msg["role"] == "user" else "Patient",
                                    "role": msg["role"],
                                    "message": msg["content"]
                                }
                                for i, msg in enumerate(st.session_state.vp_manager.get_conversation_history())
                            ],
                            "clinical_reasoning": st.session_state.clinical_reasoning
                        }

                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"session_{selected_case}_{selected_personality}_{timestamp}.json"
                        filepath = Path(filename)

                        with open(filepath, 'w') as f:
                            json.dump(session_data, f, indent=2)

                        st.success(f"✅ Saved to: {filename}")
                        st.info(f"File location: {filepath.absolute()}")

                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

            with col3:
                if st.button("📥 Download JSON", use_container_width=True):
                    try:
                        session_data = {
                            "session_metadata": {
                                "mode": "vp",
                                "case": selected_case,
                                "case_name": st.session_state.vp_manager.case_name,
                                "personality": selected_personality,
                                "total_turns": st.session_state.turn_count,
                                "session_start": st.session_state.session_start_time.isoformat(),
                                "session_end": datetime.now().isoformat()
                            },
                            "case_details": CASE_PROFILES[selected_case],
                            "personality_details": PERSONALITY_OVERLAYS[selected_personality],
                            "transcript": [
                                {
                                    "turn": i + 1,
                                    "speaker": "Clinician" if msg["role"] == "user" else "Patient",
                                    "role": msg["role"],
                                    "message": msg["content"]
                                }
                                for i, msg in enumerate(st.session_state.vp_manager.get_conversation_history())
                            ],
                            "clinical_reasoning": st.session_state.clinical_reasoning
                        }

                        json_str = json.dumps(session_data, indent=2)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"session_{selected_case}_{selected_personality}_{timestamp}.json"

                        st.download_button(
                            label="📥 Download",
                            data=json_str,
                            file_name=filename,
                            mime="application/json",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        elif active_page == "Session Actions":
            col1, col2 = st.columns(2)
            live_messages = get_session(st.session_state.sp_session_id).get("messages", [])
            sp_export_data = {
                "session_metadata": {
                    "mode": "sp",
                    "role": st.session_state.platform_role,
                    "sp_session_id": st.session_state.sp_session_id,
                    "case": selected_case,
                    "case_name": CASE_PROFILES[selected_case]["case_name"],
                    "total_turns": len(live_messages),
                    "session_start": st.session_state.session_start_time.isoformat(),
                    "session_end": datetime.now().isoformat()
                },
                "case_details": CASE_PROFILES[selected_case],
                "transcript": _sp_transcript_for_export(live_messages),
                "clinical_reasoning": st.session_state.clinical_reasoning
            }

            with col1:
                if st.button("💾 Submit", use_container_width=True, key="sp_submit_btn"):
                    try:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        if doctor_blinded_view:
                            filename = f"session_{selected_case}_{timestamp}.json"
                        else:
                            filename = f"session_sp_{selected_case}_{st.session_state.sp_session_id}_{timestamp}.json"
                        filepath = Path(filename)
                        with open(filepath, 'w') as f:
                            json.dump(sp_export_data, f, indent=2)
                        st.success(f"✅ Saved to: {filename}")
                        st.info(f"File location: {filepath.absolute()}")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

            with col2:
                json_str = json.dumps(sp_export_data, indent=2)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                if doctor_blinded_view:
                    filename = f"session_{selected_case}_{timestamp}.json"
                else:
                    filename = f"session_sp_{selected_case}_{st.session_state.sp_session_id}_{timestamp}.json"
                st.download_button(
                    label="📥 Download JSON",
                    data=json_str,
                    file_name=filename,
                    mime="application/json",
                    use_container_width=True,
                    key="sp_download_btn"
                )

# Footer
st.markdown("""
<div class="footer">
    🏥 Virtual Patient Training System | Clinical Communication Skills Practice<br>
    <small>Built on evidence-based clinical communication guidelines</small>
</div>
""", unsafe_allow_html=True)
