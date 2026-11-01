import os
import re
from io import BytesIO
from typing import Any

from pypdf import PdfReader
import streamlit as st

from database import (
    delete_reference,
    list_communications,
    list_references,
    list_reports,
    save_communication,
    save_patient_report,
    save_reference,
)


st.set_page_config(page_title="Clarity Clinic", page_icon="+", layout="wide")

TONE_OPTIONS = {
    "溫暖陪伴": "warm, reassuring, and empathetic",
    "專業簡潔": "professional, concise, and direct",
    "教學引導": "educational, structured, and explanatory",
}
COMPLEXITY_OPTIONS = {
    "一般民眾": "plain language suitable for a general adult reader",
    "高中程度": "moderate detail with medical terms explained briefly",
    "進階閱讀": "more detailed clinical language while remaining understandable",
}


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9]{2,}|[\u4e00-\u9fff]", text.lower()))


def extract_report_text(file_name: str, file_bytes: bytes) -> str:
    if file_name.lower().endswith(".pdf"):
        reader = PdfReader(BytesIO(file_bytes))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()
    return file_bytes.decode("utf-8").strip()


def retrieve_context(question: str, limit: int = 4) -> list[dict[str, Any]]:
    query_tokens = tokenize(question)
    scored: list[tuple[int, dict[str, Any]]] = []
    for reference in list_references():
        score = len(query_tokens & tokenize(reference["chunk_text"]))
        if score:
            scored.append((score, reference))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [reference for _, reference in scored[:limit]]


def make_fallback_explanation(report: str, tone: str, complexity: str,
                              context: list[dict[str, Any]]) -> str:
    first_paragraph = report.strip().split("\n\n")[0][:900]
    source_note = (
        "\n\n參考依據：" + "、".join(item["document_title"] for item in context)
        if context else "\n\n目前沒有找到相符的參考資料；以下內容僅整理你提供的報告。"
    )
    return (
        f"以下是以「{tone}」語氣、{complexity}程度整理的說明：\n\n"
        f"報告重點：{first_paragraph}\n\n"
        "請把這份整理當作和醫師討論的輔助，不要自行停藥或改變治療。"
        f"{source_note}"
    )


def generate_explanation(report: str, tone: str, complexity: str,
                         context: list[dict[str, Any]]) -> tuple[str, str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return make_fallback_explanation(report, tone, complexity, context), "local-grounded-demo"

    try:
        from openai import OpenAI

        sources = "\n\n".join(
            f"[{item['document_title']}] {item['chunk_text']}" for item in context
        ) or "No external reference matched."
        prompt = (
            "You are a medical communication assistant. Explain the report for a patient, "
            "do not diagnose, invent facts, or give treatment changes. State uncertainty. "
            f"Tone: {TONE_OPTIONS[tone]}. Reading level: {COMPLEXITY_OPTIONS[complexity]}.\n\n"
            f"REPORT:\n{report}\n\nREFERENCE CONTEXT:\n{sources}"
        )
        client = OpenAI(api_key=api_key, base_url=os.getenv("OPENAI_BASE_URL"))
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return response.choices[0].message.content or "No explanation was returned.", os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    except Exception as error:
        st.warning(f"LLM unavailable, using local demo response: {error}")
        return make_fallback_explanation(report, tone, complexity, context), "local-grounded-demo"


st.markdown("# Clarity Clinic")
st.caption("Doctor-controlled explanations with a traceable medical knowledge base")
st.warning("Demo environment: use fictional patient data. This tool does not replace clinical judgment.")

with st.sidebar:
    st.subheader("Workspace")
    patient_id = st.text_input("Patient ID", placeholder="e.g. PT-001").strip()
    doctor_id = st.text_input("Doctor ID", placeholder="e.g. DR-001").strip()
    st.divider()
    st.caption("Storage: SQLite · Retrieval: lexical chunk matching")

intake_tab, explain_tab, knowledge_tab, records_tab = st.tabs([
    "1 · Report intake", "2 · Explain report", "3 · Knowledge base", "4 · Records"
])

with intake_tab:
    st.subheader("Patient medical report")
    with st.form("report_form", clear_on_submit=True):
        title = st.text_input("Report title", placeholder="Blood test · 2026-10-31")
        file = st.file_uploader("Optional report file", type=["txt", "md", "pdf"])
        report_text = st.text_area(
            "Report content", height=260,
            placeholder="Paste the medical report text here. Remove names and identifiers for this demo.",
        )
        save_report = st.form_submit_button("Save report", type="primary")
    if save_report:
        if not patient_id or not title or not (report_text.strip() or file):
            st.error("Patient ID, report title, and report content are required.")
        else:
            if file and not report_text.strip():
                try:
                    report_text = extract_report_text(file.name, file.getvalue())
                except Exception as error:
                    st.error(f"Could not read the uploaded file: {error}")
                    st.stop()
                if not report_text:
                    st.error("The uploaded file did not contain readable text.")
                    st.stop()
            report_id = save_patient_report(patient_id, title, report_text, file.name if file else None)
            st.success(f"Saved report {report_id[:8]} for {patient_id}.")

with explain_tab:
    st.subheader("Patient-friendly explanation")
    reports = list_reports(patient_id or None)
    if not reports:
        st.info("Save a report first, then return here to generate an explanation.")
    else:
        report_map = {report["id"]: report for report in reports}
        selected_id = st.selectbox(
            "Report", list(report_map),
            format_func=lambda key: f"{report_map[key]['title']} · {report_map[key]['patient_id']}",
        )
        selected = report_map[selected_id]
        tone = st.selectbox("Communication tone", list(TONE_OPTIONS))
        complexity = st.select_slider("Complexity", options=list(COMPLEXITY_OPTIONS), value="一般民眾")
        question = st.text_input("Retrieval focus", value="key findings, meaning, and questions for the doctor")
        if st.button("Generate explanation", type="primary"):
            context = retrieve_context(question)
            explanation, model = generate_explanation(selected["report_text"], tone, complexity, context)
            st.session_state["last_explanation"] = explanation
            st.session_state["last_sources"] = context
            st.session_state["last_model"] = model
            save_communication(patient_id or selected["patient_id"], selected_id, "assistant", explanation, tone, complexity)
        if st.session_state.get("last_explanation"):
            st.markdown(st.session_state["last_explanation"])
            st.caption(f"Generated with {st.session_state.get('last_model', 'unknown')}")
            sources = st.session_state.get("last_sources", [])
            if sources:
                with st.expander("Retrieved reference passages"):
                    for source in sources:
                        st.markdown(f"**{source['document_title']}** · {source['source'] or 'source not provided'}")
                        st.write(source["chunk_text"])

with knowledge_tab:
    st.subheader("Medical reference knowledge base")
    st.caption("Each source is split into overlapping chunks before retrieval.")
    with st.form("reference_form", clear_on_submit=True):
        reference_title = st.text_input("Document title")
        publisher = st.text_input("Publisher / organization")
        source = st.text_input("Source URL or section")
        reference_file = st.file_uploader(
            "Optional reference file", type=["txt", "md", "pdf"]
        )
        reference_text = st.text_area("Reference content", height=260)
        add_reference = st.form_submit_button("Chunk and save reference")
    if add_reference:
        if not reference_title or not (reference_text.strip() or reference_file):
            st.error("Document title and reference content are required.")
        else:
            if reference_file and not reference_text.strip():
                try:
                    reference_text = extract_report_text(
                        reference_file.name, reference_file.getvalue()
                    )
                except Exception as error:
                    st.error(f"Could not read the uploaded file: {error}")
                    st.stop()
                if not reference_text:
                    st.error("The uploaded file did not contain readable text.")
                    st.stop()
            count = save_reference(reference_title, publisher, source, reference_text)
            st.success(f"Saved {count} retrieval chunks.")
    references = list_references()
    st.metric("Indexed chunks", len(references))
    reference_groups: dict[tuple[str, str, str], int] = {}
    for reference in references:
        key = (
            reference["document_title"],
            reference["publisher"] or "",
            reference["source"] or "",
        )
        reference_groups[key] = reference_groups.get(key, 0) + 1
    if reference_groups:
        selected_reference = st.selectbox(
            "Reference to remove",
            list(reference_groups),
            format_func=lambda key: (
                f"{key[0]} · {key[1] or 'publisher not provided'} · "
                f"{reference_groups[key]} chunks"
            ),
        )
        if st.button("Remove selected reference", type="secondary"):
            title, publisher, source = selected_reference
            deleted = delete_reference(title, publisher, source)
            st.success(f"Removed {title} ({deleted} chunks).")

with records_tab:
    st.subheader("Doctor-patient communication records")
    if not patient_id:
        st.info("Enter a Patient ID in the sidebar to view records.")
    else:
        records = list_communications(patient_id)
        if not records:
            st.info("No communication records for this patient yet.")
        for record in records:
            label = f"{record['sender_role']} · {record['created_at'][:16].replace('T', ' ')}"
            with st.expander(label):
                st.write(record["message_text"])
                if record["tone"]:
                    st.caption(f"Tone: {record['tone']} · Complexity: {record['complexity']}")
