import os
import time
import base64
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import APIError

from pdf_processor import (
    extract_text_by_pages,
    format_pages_for_context,
    get_pdf_metadata,
    extract_cited_pages,
    render_pdf_page_image
)

# Load environment variables (.env)
load_dotenv(override=True)

@st.cache_data(show_spinner=False, ttl=600)
def fetch_live_models(api_key: str):
    """Dynamically queries Google AI Studio to discover which models are active for this key."""
    if not api_key:
        return ["gemini-3.8-flash", "gemini-3.8-pro"]
    try:
        client = genai.Client(api_key=api_key)
        valid = []
        for m in client.models.list():
            actions = getattr(m, "supported_actions", []) or []
            if "generateContent" in actions:
                m_name = m.name.replace("models/", "")
                # Exclude embeddings, audio-only, vision-only, and search models
                if "gemini" in m_name and not any(x in m_name for x in ["embedding", "imagen", "aqa", "vision"]):
                    valid.append(m_name)
        # Prioritize 3.8-flash first if available
        if "gemini-3.8-flash" in valid:
            valid.remove("gemini-3.8-flash")
            valid.insert(0, "gemini-3.8-flash")
        return valid if valid else ["gemini-3.8-flash", "gemini-3.8-pro"]
    except Exception:
        return ["gemini-3.8-flash", "gemini-3.8-pro"]


# Page configuration
st.set_page_config(
    page_title="PDF Intelligence • Claude Style",
    page_icon="✳️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- CLAUDE.AI DESIGN SYSTEM CSS ---------------- #
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    /* Global Typography & Palette */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: #2D2B28;
    }

    /* Main Container Warm Paper Background */
    .stApp, [data-testid="stAppViewContainer"] {
        background-color: #FAF8F5 !important;
    }

    [data-testid="stHeader"] {
        background-color: transparent !important;
    }

    /* Claude's Signature Serif Headings */
    h1, h2, h3, .claude-serif {
        font-family: 'Newsreader', Georgia, serif !important;
        font-weight: 500 !important;
        color: #2D2B28 !important;
        letter-spacing: -0.02em !important;
    }

    h1 {
        font-size: 2.3rem !important;
    }

    /* Sidebar - Warm Parchment Drawer */
    [data-testid="stSidebar"] {
        background-color: #F4F0E8 !important;
        border-right: 1px solid #E8E2D5 !important;
    }

    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        color: #8C8273 !important;
        margin-top: 10px !important;
    }

    /* Claude Terracotta Accent Buttons */
    .stButton button {
        background-color: #FAF8F5 !important;
        color: #4A443A !important;
        border: 1px solid #DFD9CE !important;
        border-radius: 10px !important;
        font-weight: 500 !important;
        transition: all 0.15s ease-in-out !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
    }
    .stButton button:hover {
        background-color: #F0EAE1 !important;
        border-color: #C96442 !important;
        color: #C96442 !important;
    }

    /* Document Status Card (Claude Artifact Style) */
    .claude-card {
        background-color: #FFFFFF;
        border: 1px solid #EAE5DC;
        border-radius: 14px;
        padding: 20px;
        margin-bottom: 24px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02), 0 1px 3px rgba(0, 0, 0, 0.02);
    }

    .claude-badge {
        display: inline-flex;
        align-items: center;
        background-color: #F4EFEB;
        color: #C96442;
        border: 1px solid #EBDED7;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.01em;
        margin-right: 8px;
    }

    .claude-tag {
        display: inline-block;
        background-color: #F3EFE6;
        color: #5C5549;
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 0.76rem;
        font-weight: 500;
        margin-right: 6px;
    }

    /* Chat Messages Styling */
    [data-testid="stChatMessage"] {
        background: transparent !important;
        padding: 18px 0 !important;
        border-bottom: 1px solid #F0EBE2 !important;
    }

    /* User Message Bubble */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        background-color: transparent !important;
    }
    
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stMarkdownContainer"] {
        background-color: #F0ECE1;
        border: 1px solid #E5DFD2;
        border-radius: 18px 18px 4px 18px;
        padding: 12px 18px;
        display: inline-block;
        max-width: 85%;
        color: #2D2B28;
    }

    /* Assistant Message - Editorial Elegance */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) [data-testid="stMarkdownContainer"] {
        line-height: 1.7;
        font-size: 1.02rem;
        color: #2D2B28;
    }

    /* File Uploader Claude Style */
    [data-testid="stFileUploader"] {
        background-color: #FFFFFF;
        border: 1.5px dashed #DDD7CC;
        border-radius: 14px;
        padding: 14px;
        transition: border-color 0.2s ease;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: #C96442;
    }

    /* Input Floating Bar */
    [data-testid="stChatInput"] {
        border-radius: 24px !important;
        border: 1.5px solid #DDD6CB !important;
        background-color: #FFFFFF !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04) !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    }
    [data-testid="stChatInput"]:focus-within {
        border-color: #C96442 !important;
        box-shadow: 0 4px 20px rgba(201, 100, 66, 0.12) !important;
    }

    /* Citation callouts */
    blockquote {
        border-left: 3px solid #C96442 !important;
        background: #F8F5EE !important;
        padding: 8px 14px !important;
        border-radius: 0 8px 8px 0 !important;
        margin: 12px 0 !important;
    }
</style>
""", unsafe_allow_html=True)


# ---------------- SIDEBAR ---------------- #
with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
        <span style="font-size: 1.4rem; color: #C96442;">✳️</span>
        <span style="font-family: 'Newsreader', serif; font-size: 1.35rem; font-weight: 600; color: #2D2B28;">Claude PDF</span>
    </div>
    <div style="font-size: 0.8rem; color: #7A7264; margin-bottom: 20px;">Workspace & Intelligence Controls</div>
    """, unsafe_allow_html=True)

    # 1. API Key configuration (read from .env or Streamlit Cloud Secrets)
    load_dotenv(override=True)
    active_api_key = (os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")).strip()
    if not active_api_key and hasattr(st, "secrets"):
        try:
            active_api_key = str(st.secrets.get("GEMINI_API_KEY", "") or st.secrets.get("GOOGLE_API_KEY", "")).strip()
        except Exception:
            pass

    if active_api_key:
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 8px; font-size: 0.82rem; color: #2F7C4F; font-weight: 500; background: #EEF6F0; border: 1px solid #D6EBDC; padding: 8px 12px; border-radius: 8px; margin-bottom: 8px;">
            <span>●</span> API Key Connected
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 8px; font-size: 0.82rem; color: #B34026; font-weight: 500; background: #FDF1ED; border: 1px solid #F6D6CC; padding: 8px 12px; border-radius: 8px; margin-bottom: 8px;">
            <span>⚠️</span> Missing API Key
        </div>
        """, unsafe_allow_html=True)
        st.caption("Please add `GEMINI_API_KEY` to your `.env` or Streamlit Cloud Secrets.")

    st.markdown("<hr style='border: none; border-top: 1px solid #E6E0D3; margin: 18px 0;'>", unsafe_allow_html=True)

    # 2. Model selection
    live_models = fetch_live_models(active_api_key)
    selected_model = st.selectbox(
        "Intelligence Engine",
        options=live_models,
        index=0,
        help="Active verified models for this key."
    )

    # 3. Behavior settings
    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=0.2,
        step=0.05,
        help="Lower values (0.1 - 0.2) ensure factual adherence to the PDF without hallucination."
    )

    st.markdown("<hr style='border: none; border-top: 1px solid #E6E0D3; margin: 18px 0;'>", unsafe_allow_html=True)

    # 4. Clear chat action
    if st.button("Start Fresh Conversation", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

    st.markdown("""
    <div style="margin-top: 30px; font-size: 0.75rem; color: #9E9689; text-align: center;">
        Claude.ai Aesthetic • Powered by Gemini 3.8
    </div>
    """, unsafe_allow_html=True)


# ---------------- SESSION STATE INIT ---------------- #
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "pdf_context" not in st.session_state:
    st.session_state.pdf_context = None

if "pdf_metadata" not in st.session_state:
    st.session_state.pdf_metadata = None

if "current_file_name" not in st.session_state:
    st.session_state.current_file_name = None

if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None

if "pages_data" not in st.session_state:
    st.session_state.pages_data = None

if "viewer_page" not in st.session_state:
    st.session_state.viewer_page = 1

if "reset_viewer" not in st.session_state:
    st.session_state.reset_viewer = False


# ---------------- DOCUMENT VIEWER MODAL ---------------- #
@st.dialog("📄 Document Inspector", width="large")
def view_document_dialog(target_page: int = 1):
    meta = st.session_state.get("pdf_metadata", {}) or {}
    total_pages = meta.get("total_pages", 1)
    
    if st.session_state.get("reset_viewer"):
        st.session_state.viewer_page = max(1, min(target_page, total_pages))
        st.session_state.reset_viewer = False

    current_page = st.session_state.get("viewer_page", max(1, min(target_page, total_pages)))

    # Navigation Toolbar
    col_nav1, col_nav2, col_nav3, col_nav4 = st.columns([1, 2, 1, 2])
    with col_nav1:
        if st.button("◀ Prev", disabled=(current_page <= 1), key="dlg_prev", use_container_width=True):
            st.session_state.viewer_page = max(1, current_page - 1)
            st.rerun()
    with col_nav2:
        st.markdown(
            f"<div style='text-align: center; padding-top: 6px; font-weight: 600; font-family: Newsreader, serif; font-size: 1.15rem; color: #2D2B28;'>"
            f"Page {current_page} of {total_pages}"
            f"</div>",
            unsafe_allow_html=True
        )
    with col_nav3:
        if st.button("Next ▶", disabled=(current_page >= total_pages), key="dlg_next", use_container_width=True):
            st.session_state.viewer_page = min(total_pages, current_page + 1)
            st.rerun()
    with col_nav4:
        new_page = st.selectbox(
            "Jump to page",
            options=list(range(1, total_pages + 1)),
            index=current_page - 1,
            label_visibility="collapsed",
            key="dlg_jump_select"
        )
        if new_page != current_page:
            st.session_state.viewer_page = new_page
            st.rerun()

    st.markdown("<hr style='border: none; border-top: 1px solid #EAE5DC; margin: 10px 0 16px 0;'>", unsafe_allow_html=True)

    tab_vis, tab_txt, tab_embed = st.tabs(["🖼️ High-Res Page View", "📝 Extracted Page Text", "↗️ Full PDF Embed"])

    with tab_vis:
        if st.session_state.get("pdf_bytes"):
            with st.spinner(f"Rendering Page {current_page}..."):
                img = render_pdf_page_image(st.session_state.pdf_bytes, current_page, scale=2.0)
                if img:
                    st.image(img, use_container_width=True, caption=f"{st.session_state.current_file_name} — Page {current_page}")
                else:
                    st.warning("Unable to render image for this page.")
        else:
            st.info("No document binary loaded.")

    with tab_txt:
        matched_text = ""
        if st.session_state.get("pages_data"):
            for p in st.session_state.pages_data:
                if p["page"] == current_page:
                    matched_text = p["text"]
                    break
        if matched_text:
            st.markdown(f"**Text on Page {current_page}:**")
            st.text_area("Page Text", value=matched_text, height=420, label_visibility="collapsed")
        else:
            st.info("No selectable text extracted on this page (may contain diagrams, formulas, or images).")

    with tab_embed:
        if st.session_state.get("pdf_bytes"):
            b64_pdf = base64.b64encode(st.session_state.pdf_bytes).decode('utf-8')
            pdf_embed_html = (
                f'<iframe src="data:application/pdf;base64,{b64_pdf}#page={current_page}" '
                f'width="100%" height="600" type="application/pdf" style="border: 1px solid #E5DFD2; border-radius: 8px;"></iframe>'
            )
            st.markdown(pdf_embed_html, unsafe_allow_html=True)
            st.download_button(
                label=f"⬇️ Download {st.session_state.current_file_name}",
                data=st.session_state.pdf_bytes,
                file_name=st.session_state.current_file_name,
                mime="application/pdf",
                key="dlg_download_btn"
            )


# ---------------- MAIN HEADER & FILE UPLOADER ---------------- #
st.markdown("""
<div style="margin-bottom: 28px; padding-top: 8px;">
    <div style="display: inline-flex; align-items: center; gap: 8px; margin-bottom: 8px;">
        <span style="font-size: 1.2rem; color: #C96442;">✳️</span>
        <span style="font-size: 0.85rem; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: #8A8173;">DOCUMENT INTELLIGENCE</span>
    </div>
    <h1 style="margin: 0; font-size: 2.4rem;">What shall we explore today?</h1>
    <p style="color: #6E685D; font-size: 1.05rem; margin-top: 6px; font-weight: 400;">
        Upload a document to analyze its contents, extract structured findings, and cite verified page sources.
    </p>
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Upload Document (PDF)",
    type=["pdf"],
    help="Upload contracts, reports, manuals, academic papers, or books.",
    label_visibility="collapsed"
)

# Process PDF when a new file is uploaded
if uploaded_file is not None:
    if st.session_state.pdf_bytes is None or st.session_state.current_file_name != uploaded_file.name:
        with st.spinner("Analyzing document structure and indexing page coordinates..."):
            try:
                pdf_bytes = uploaded_file.getvalue()
                pages_data = extract_text_by_pages(uploaded_file)
                st.session_state.pdf_bytes = pdf_bytes
                st.session_state.pages_data = pages_data
                st.session_state.pdf_metadata = get_pdf_metadata(uploaded_file, pages_data)
                st.session_state.pdf_context = format_pages_for_context(pages_data)
                st.session_state.current_file_name = uploaded_file.name
                st.session_state.chat_history = []
            except Exception as e:
                st.error(f"Error processing PDF: {str(e)}", icon="🚨")

# Display Document Card (Claude Artifact Style)
if st.session_state.pdf_metadata and st.session_state.current_file_name:
    meta = st.session_state.pdf_metadata
    fname = st.session_state.current_file_name
    chars_formatted = f"{meta['total_characters']:,}"
    
    col_card, col_action = st.columns([4, 1.4])
    with col_card:
        st.markdown(f"""
        <div class="claude-card" style="margin-bottom: 12px;">
            <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;">
                <div style="display: flex; align-items: center; gap: 14px;">
                    <div style="width: 44px; height: 44px; border-radius: 10px; background-color: #F6F1EA; border: 1px solid #EBE4D8; display: flex; align-items: center; justify-content: center; font-size: 1.4rem;">
                        📄
                    </div>
                    <div>
                        <div style="font-weight: 600; font-size: 1.05rem; color: #2D2B28;">{fname}</div>
                        <div style="margin-top: 4px; display: flex; gap: 6px; align-items: center;">
                            <span class="claude-badge">{meta['total_pages']} Pages</span>
                            <span class="claude-tag">{chars_formatted} characters</span>
                            <span class="claude-tag">{meta['pages_with_text']} with text</span>
                        </div>
                    </div>
                </div>
                <div style="color: #2F7C4F; font-size: 0.85rem; font-weight: 600; display: flex; align-items: center; gap: 6px;">
                    <span>●</span> Indexed & Ready
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_action:
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        if st.button("📖 Inspect Document", use_container_width=True, key="inspect_all_btn"):
            st.session_state.reset_viewer = True
            view_document_dialog(1)

    if meta["is_scanned_suspicion"]:
        st.warning(
            "⚠️ Notice: Most pages appear to have very little selectable text. "
            "If this document is a scanned image, standard text extraction may be limited.",
            icon="⚠️"
        )


# ---------------- CHAT INTERFACE ---------------- #
# Display message history
for msg_idx, message in enumerate(st.session_state.chat_history):
    avatar_icon = "👤" if message["role"] == "user" else "✳️"
    with st.chat_message(message["role"], avatar=avatar_icon):
        st.markdown(message["content"])

        # Clickable source page buttons for assistant responses
        if message["role"] == "assistant" and st.session_state.get("pdf_bytes"):
            cited_pages = extract_cited_pages(message["content"])
            if cited_pages:
                st.markdown(
                    "<div style='margin-top: 10px; margin-bottom: 6px; font-size: 0.78rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #8A8173;'>"
                    "Verified Source Pages (Click to View):"
                    "</div>",
                    unsafe_allow_html=True
                )
                btn_cols = st.columns(min(len(cited_pages), 6))
                for c_i, p_num in enumerate(cited_pages[:6]):
                    with btn_cols[c_i]:
                        if st.button(f"🔍 Page {p_num}", key=f"cite_btn_{msg_idx}_{p_num}_{c_i}"):
                            st.session_state.reset_viewer = True
                            view_document_dialog(p_num)

# Prompt input
user_query = st.chat_input("Reply to Claude or ask a question about your document...")

if user_query:
    # Validation checks
    if not active_api_key:
        st.error("Please add your Gemini API Key to `.env` or Streamlit Cloud Secrets before asking a question.", icon="🔑")
    elif not st.session_state.pdf_context:
        st.warning("Please upload a PDF document first.", icon="📄")
    else:
        # Append and display user message
        st.session_state.chat_history.append({"role": "user", "content": user_query})
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_query)

        # Build System Instructions
        system_instruction = (
            "You are a professional, highly rigorous AI document analysis agent. "
            "Your objective is to answer questions strictly based on the provided PDF document.\n\n"
            "BEHAVIOR RULES:\n"
            "1. Tone: Professional, authoritative, objective, and precise.\n"
            "2. Grounding: Answer ONLY using facts directly stated or clearly implied by the document. "
            "If the information is not in the document, explicitly say: "
            "'The uploaded document does not contain information to answer this question.'\n"
            "3. Structure:\n"
            "   - Provide a direct, concise executive summary answer first.\n"
            "   - Use bullet points for structured details, lists, or steps when helpful.\n"
            "   - ALWAYS include a 'Sources / Citations' section citing the specific page number(s) "
            "where the information was retrieved (e.g., '[Page 3]', '[Pages 5-6]').\n"
            "4. Never hallucinate or assume unstated facts."
        )

        # Prepare context prompt
        # We pass previous chat history for conversation continuity
        conversation_context = ""
        if len(st.session_state.chat_history) > 1:
            conversation_context = "\n\nPrevious conversation turns:\n"
            for turn in st.session_state.chat_history[:-1]:
                role_label = "User" if turn["role"] == "user" else "Assistant"
                conversation_context += f"{role_label}: {turn['content']}\n"

        prompt_payload = (
            f"DOCUMENT CONTENT (with page markers):\n"
            f"{st.session_state.pdf_context}\n\n"
            f"{conversation_context}\n\n"
            f"CURRENT USER QUESTION:\n{user_query}\n\n"
            f"Please respond following all instructions and page citation rules."
        )

        # Generate Assistant response with streaming & intelligent retry
        with st.chat_message("assistant", avatar="✳️"):
            response_container = st.empty()
            full_response = ""
            status_container = st.empty()

            # Prioritize selected model, followed only by verified available models from live_models
            candidate_models = [selected_model]
            for m in live_models:
                if m not in candidate_models:
                    candidate_models.append(m)

            client = genai.Client(api_key=active_api_key)
            handled = False

            for model_to_try in candidate_models:
                # Up to 3 attempts with exponential backoff on demand spikes
                max_attempts = 3
                retry_delays = [2, 3, 5]

                for attempt in range(max_attempts):
                    try:
                        response = client.models.generate_content_stream(
                            model=model_to_try,
                            contents=prompt_payload,
                            config=types.GenerateContentConfig(
                                system_instruction=system_instruction,
                                temperature=temperature,
                            )
                        )

                        for chunk in response:
                            if chunk.text:
                                full_response += chunk.text
                                response_container.markdown(full_response + "▌")

                        response_container.markdown(full_response)
                        st.session_state.chat_history.append({"role": "assistant", "content": full_response})
                        status_container.empty()
                        handled = True
                        st.rerun()

                    except APIError as api_err:
                        err_text = str(api_err)
                        # Transient 503 (High Demand) or 429 (Rate Limit) -> backoff & retry
                        if ("503" in err_text or "UNAVAILABLE" in err_text or "429" in err_text):
                            if attempt < max_attempts - 1:
                                delay = retry_delays[attempt]
                                status_container.warning(
                                    f"⏳ Gemini servers are experiencing temporary high demand. Retrying in {delay}s (Attempt {attempt + 1}/{max_attempts})...",
                                    icon="⏳"
                                )
                                time.sleep(delay)
                                continue
                        # If not a temporary demand error or exhausted retries for this model, break to next model
                        break
                    except Exception as e:
                        status_container.empty()
                        response_container.error(f"**Unexpected Error:** {str(e)}")
                        handled = True
                        break

                if handled:
                    break

            if not handled and not full_response:
                status_container.empty()
                response_container.error(
                    "**Service Temporarily Busy:** All retry attempts encountered high server traffic. "
                    "Please wait a few seconds and try submitting your question again."
                )
