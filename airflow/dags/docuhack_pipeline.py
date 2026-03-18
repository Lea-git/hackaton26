"""
docuhack_pipeline.py — DAG Airflow pour le pipeline DocuHack.

Chaîne : scan_raw → ingest → mock_ocr → ner → validate → [populate_crm, populate_conformite]
"""

import sys
import logging
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator, ShortCircuitOperator

# Ajouter les paths pour les imports
sys.path.insert(0, "/opt/airflow")
sys.path.insert(0, "/opt/airflow/backend")

from docuhack_tasks.ingest import scan_raw_zone, ingest_documents
from docuhack_tasks.ocr_mock import mock_ocr
from docuhack_tasks.ner_structure import ner_structuration
from docuhack_tasks.validate import validate_documents
from docuhack_tasks.populate_crm import populate_crm
from docuhack_tasks.populate_conformite import populate_conformite

logger = logging.getLogger(__name__)


def _on_failure(context):
    task_id = context.get("task_instance").task_id
    logger.error(f"[FAILURE] Tâche '{task_id}' échouée: {context.get('exception')}")


def _on_success(context):
    task_id = context.get("task_instance").task_id
    logger.info(f"[SUCCESS] Tâche '{task_id}' terminée avec succès")


def _check_new_files(**context):
    """ShortCircuit : retourne True si des fichiers sont à traiter."""
    new_files = scan_raw_zone(**context)
    if not new_files:
        logger.info("[scan] Aucun nouveau fichier, pipeline skip")
        return False
    # Stocker la liste dans XCom sous la clé 'new_files'
    context["ti"].xcom_push(key="new_files", value=new_files)
    return True


default_args = {
    "owner": "docuhack",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
    "on_failure_callback": _on_failure,
    "on_success_callback": _on_success,
}

with DAG(
    dag_id="docuhack_document_pipeline",
    default_args=default_args,
    description="Pipeline de traitement documentaire DocuHack : raw → clean → curated → CRM/Conformité",
    schedule_interval="*/5 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["docuhack", "pipeline", "documents"],
) as dag:

    scan_raw = ShortCircuitOperator(
        task_id="scan_raw_zone",
        python_callable=_check_new_files,
        provide_context=True,
    )

    ingest = PythonOperator(
        task_id="ingest_documents",
        python_callable=ingest_documents,
        provide_context=True,
    )

    ocr = PythonOperator(
        task_id="mock_ocr",
        python_callable=mock_ocr,
        provide_context=True,
    )

    ner = PythonOperator(
        task_id="ner_structuration",
        python_callable=ner_structuration,
        provide_context=True,
    )

    validate = PythonOperator(
        task_id="validate_documents",
        python_callable=validate_documents,
        provide_context=True,
    )

    crm = PythonOperator(
        task_id="populate_crm",
        python_callable=populate_crm,
        provide_context=True,
    )

    conformite = PythonOperator(
        task_id="populate_conformite",
        python_callable=populate_conformite,
        provide_context=True,
    )

    # Chaîne de tâches
    scan_raw >> ingest >> ocr >> ner >> validate >> [crm, conformite]
