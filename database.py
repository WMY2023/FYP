import os
from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database


MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
DATABASE_NAME = "medical_reports"


_client = MongoClient(MONGODB_URI)
database: Database = _client[DATABASE_NAME]

patient_reports: Collection = database["patient_reports"]
generated_reports: Collection = database["generated_reports"]
external_materials: Collection = database["external_materials"]


def connect_to_database() -> str:
    """Check that MongoDB is reachable and return a status message."""
    _client.admin.command("ping")
    return "MongoDB connection successful"


def create_indexes() -> None:
    """Create indexes used by the application."""
    patient_reports.create_index("patient_id")
    generated_reports.create_index("patient_id")
    generated_reports.create_index("patient_report_id")
    external_materials.create_index("title")


def save_patient_report(
    patient_id: str,
    report_text: str,
    report_type: str | None = None,
    file_name: str | None = None,
) -> Any:
    """Save an original patient report and return its MongoDB ID."""
    result = patient_reports.insert_one({
        "patient_id": patient_id,
        "report_type": report_type,
        "report_text": report_text,
        "file_name": file_name,
    })
    return result.inserted_id


def save_generated_report(
    patient_report_id: Any,
    patient_id: str,
    generated_text: str,
    tone: str,
    model_name: str | None = None,
) -> Any:
    """Save an LLM-generated report and return its MongoDB ID."""
    result = generated_reports.insert_one({
        "patient_report_id": patient_report_id,
        "patient_id": patient_id,
        "generated_text": generated_text,
        "tone": tone,
        "model_name": model_name,
    })
    return result.inserted_id


def save_external_material(
    title: str,
    content: str,
    source: str | None = None,
    material_type: str | None = None,
) -> Any:
    """Save an external medical reference and return its MongoDB ID."""
    result = external_materials.insert_one({
        "title": title,
        "source": source,
        "material_type": material_type,
        "content": content,
    })
    return result.inserted_id


def get_patient_reports(patient_id: str) -> list[dict[str, Any]]:
    """Return all original reports belonging to a patient."""
    return list(patient_reports.find({"patient_id": patient_id}))


def get_generated_reports(patient_id: str) -> list[dict[str, Any]]:
    """Return all generated reports belonging to a patient."""
    return list(generated_reports.find({"patient_id": patient_id}))


create_indexes()
