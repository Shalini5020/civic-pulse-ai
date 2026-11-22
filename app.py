import warnings
warnings.filterwarnings("ignore")

import logging
logging.getLogger("streamlit").setLevel(logging.ERROR)

import os
import json
import re
import streamlit as st
from google import genai
from google.genai import types
from prompts import get_civic_audit_prompt

st.set_page_config(page_title="CivicPulse AI - Public Policy & Notice Auditor", page_icon="🏛️", layout="wide")

st.title("🏛️ CivicPulse AI: Public Policy & Notice Auditor")
st.markdown("Upload any **Government Scheme PDF, RTI Reply, or Municipal Notice Image**. The AI translates complex legal jargon into plain language and highlights hidden conditions.")

# API Key बैकग्राउंड (Environment या Streamlit Secrets) से अपने आप लोड होगी
try:
    api_key = os.environ.get("GEMINI_API_KEY") or st.secrets["GEMINI_API_KEY"]
except Exception:
    api_key = os.environ.get("GEMINI_API_KEY", "")

with st.sidebar:
    st.header("⚙️ Settings")
    language = st.selectbox("Output Language / भाषा चुनें", ["English", "Hindi (सरल हिंदी)"])

uploaded_file = st.file_uploader("📄 Upload Government Policy (PDF) or Notice Photo (JPG/PNG)", type=["pdf", "png", "jpg", "jpeg"])

if st.button("🔍 Audit Civic Document", type="primary"):
    if not api_key:
        st.error("System configuration pending: Please set GEMINI_API_KEY in terminal or Streamlit Cloud Secrets.")
    elif not uploaded_file:
        st.warning("Please upload a PDF or image file first!")
    else:
        with st.spinner("Scanning and auditing document..."):
            try:
                client = genai.Client(api_key=api_key)
                prompt = get_civic_audit_prompt(language)

                doc_part = types.Part.from_bytes(
                    data=uploaded_file.getvalue(),
                    mime_type=uploaded_file.type,
                )

                # अगर मुख्य मॉडल व्यस्त (503) हो, तो अपने आप बैकअप मॉडल पर स्विच होगा
                models_to_try = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-2.0-flash"]
                response = None
                last_error = None

                for model_name in models_to_try:
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=[doc_part, prompt],
                        )
                        break
                    except Exception as err:
                        last_error = err
                        continue

                if response is None:
                    raise last_error

                json_match = re.search(r"\{[\s\S]*\}", response.text)
                clean_json = json_match.group(0) if json_match else response.text
                data = json.loads(clean_json)

                st.info(f"**📌 Plain-Language Summary:** {data.get('summary', '')}")

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.success("### 🟢 Citizen Benefits & Rights")
                    for item in data.get("Green_Flags", []):
                        st.write(f"• {item}")

                with col2:
                    st.warning("### 🟡 Eligibility & Documents")
                    for item in data.get("Yellow_Flags", []):
                        st.write(f"• {item}")

                with col3:
                    st.error("### 🔴 Hidden Traps & Deadlines")
                    for item in data.get("Red_Flags", []):
                        st.write(f"• {item}")

                st.markdown(f"**👉 Recommended Next Step:** {data.get('next_step', '')}")

                spoken_text = f"Summary: {data.get('summary', '')}. Citizen Benefits: {' '.join(data.get('Green_Flags', []))}. Hidden Traps: {' '.join(data.get('Red_Flags', []))}"
                lang_code = "hi-IN" if "Hindi" in language else "en-IN"
                
                st.components.v1.html(f"""
                    <button onclick="const u = new SpeechSynthesisUtterance({json.dumps(spoken_text)}); u.lang='{lang_code}'; window.speechSynthesis.speak(u);" 
                    style="padding:10px 18px; background:#1e3a8a; color:white; border:none; border-radius:6px; cursor:pointer; font-size:15px; font-weight:bold;">
                        🔊 Listen Aloud (Accessibility Mode)
                    </button>
                """, height=55)

            except Exception as e:
                st.error(f"Audit Error: {str(e)}")
