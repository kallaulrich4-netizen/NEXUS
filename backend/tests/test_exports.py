"""
Tests de l'utilitaire d'export partagé. Nécessitent : pip install -r requirements.txt
(reportlab, python-docx, openpyxl, python-pptx)
Lancer avec : pytest tests/ -v
"""
from app.core.exports import (
    ExportDocument, ExportSection,
    export_to_pdf, export_to_word, export_to_excel, export_to_powerpoint,
)

SAMPLE_DOCUMENT = ExportDocument(
    title="Rapport de test",
    subtitle="Sous-titre de test",
    sections=[
        ExportSection(
            heading="Résumé",
            paragraphs=["Ceci est un paragraphe de test.", "Un second paragraphe."],
        ),
        ExportSection(
            heading="Données",
            table_headers=["Catégorie", "Montant"],
            table_rows=[["Loyer", "100000"], ["Alimentation", "50000"]],
        ),
    ],
)


def test_export_to_pdf_produces_valid_pdf_bytes():
    content = export_to_pdf(SAMPLE_DOCUMENT)
    assert content.startswith(b"%PDF")
    assert len(content) > 500


def test_export_to_word_produces_valid_docx_bytes():
    content = export_to_word(SAMPLE_DOCUMENT)
    # Un .docx est une archive ZIP : signature de fichier "PK".
    assert content[:2] == b"PK"
    assert len(content) > 500


def test_export_to_excel_produces_valid_xlsx_bytes():
    content = export_to_excel(SAMPLE_DOCUMENT)
    assert content[:2] == b"PK"
    assert len(content) > 500


def test_export_to_powerpoint_produces_valid_pptx_bytes():
    content = export_to_powerpoint(SAMPLE_DOCUMENT)
    assert content[:2] == b"PK"
    assert len(content) > 500


def test_export_handles_document_without_tables():
    document = ExportDocument(title="Simple", sections=[ExportSection(paragraphs=["Un seul paragraphe."])])
    pdf_content = export_to_pdf(document)
    word_content = export_to_word(document)
    assert pdf_content.startswith(b"%PDF")
    assert word_content[:2] == b"PK"
