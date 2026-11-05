# Clarity Clinic

A Streamlit prototype for doctor-controlled, patient-friendly medical report explanations.

## Included requirements

- Patient medical reports are stored in SQLite.
- Reports can be pasted or uploaded as TXT, Markdown, or text-based PDF files.
- Doctors can manage reports, explanations, references, and communication records.
- Patients only access the report explanation workflow.
- Reference documents are split into overlapping chunks and retrieved by lexical relevance.
- Retrieved passages are shown with the generated explanation for traceability.
- Doctor-patient and assistant communication records are stored.
- OpenAI generation is optional; without an API key the app runs with a local grounded demo response.

## Run

```powershell
cd C:\Users\wmywm\Desktop\FYP
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Optional `.env` values can be loaded by your shell or VS Code:

```text
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
DATABASE_PATH=data/medical_assistant.db
```

Use fictional or de-identified data. This prototype is not a diagnostic tool, and authentication, authorization, audit controls, encryption, and clinical review workflows are still required before production use.
