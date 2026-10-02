"""Batch extraction of PDF documents to Markdown using pdfplumber.
Preserves table structures as Markdown grids and extracts textual content.
"""

import os
import re
from typing import Optional
import pdfplumber

SOURCE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "rag_data"))
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "extracted_md"))


def sanitize_filename(filename: str) -> str:
    """Convert raw PDF filename to clean lowercase snake_case markdown filename."""
    base_name = os.path.splitext(filename)[0]
    # Remove accents/special characters
    clean = base_name.lower()
    clean = re.sub(r"[’'_\-\s]+", "_", clean)
    clean = re.sub(r"[éèêë]", "e", clean)
    clean = re.sub(r"[àâä]", "a", clean)
    clean = re.sub(r"[îï]", "i", clean)
    clean = re.sub(r"[ôö]", "o", clean)
    clean = re.sub(r"[ùûü]", "u", clean)
    clean = re.sub(r"[ç]", "c", clean)
    clean = re.sub(r"[^a-z0-9_]", "", clean)
    clean = re.sub(r"_+", "_", clean).strip("_")
    return f"{clean}.md"


def is_valid_data_table(table) -> bool:
    """Return True only if the table is a genuine data table (multi-column, multi-row)."""
    if not table or len(table) < 2:
        return False
    num_cols = len(table[0])
    if num_cols < 2:
        return False
    
    # Genuine tables must have at least 2 non-empty cells in the first row (header)
    header_non_empty = sum(1 for cell in table[0] if cell and str(cell).strip())
    if header_non_empty < 2:
        return False

    # Ensure table has substantial non-empty cells overall
    non_empty = sum(1 for row in table for cell in row if cell and str(cell).strip())
    total = len(table) * num_cols
    return (non_empty / total) >= 0.25


def extract_pdf_to_markdown(pdf_path: str, output_path: str) -> None:
    """Extract a single PDF file to Markdown with tables and text."""
    pdf_filename = os.path.basename(pdf_path)
    print(f"Extraction en cours : {pdf_filename} -> {os.path.basename(output_path)}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with pdfplumber.open(pdf_path) as pdf, open(output_path, "w", encoding="utf-8") as out:
        out.write(f"# Document : {pdf_filename}\n\n")

        for i, page in enumerate(pdf.pages):
            out.write(f"## PAGE {i + 1}\n\n")

            # 1. Extraction des véritables tableaux (grilles multi-colonnes)
            tables = page.extract_tables()
            valid_tables = [t for t in tables if is_valid_data_table(t)]

            if valid_tables:
                out.write("### Tableaux détectés :\n\n")
                for table in valid_tables:
                    for row_idx, row in enumerate(table):
                        clean_row = [str(cell).replace("\n", " ").strip() if cell else "" for cell in row]
                        out.write("| " + " | ".join(clean_row) + " |\n")
                        # Ligne de séparation après en-tête
                        if row_idx == 0:
                            out.write("| " + " | ".join(["---"] * len(clean_row)) + " |\n")
                    out.write("\n\n")

            # 2. Extraction du texte
            text = page.extract_text()
            if text:
                out.write("### Texte extrait :\n\n")
                out.write(text.strip() + "\n\n")

            out.write("\n" + "---" * 10 + "\n\n")


def extract_all_pdfs(source_dir: str = SOURCE_DIR, output_dir: str = OUTPUT_DIR) -> None:
    """Batch extract all PDFs in source_dir and write markdown files in output_dir."""
    if not os.path.exists(source_dir):
        print(f"Erreur : Le dossier source '{source_dir}' n'existe pas.")
        return

    pdf_files = [f for f in os.listdir(source_dir) if f.lower().endswith(".pdf")]

    if not pdf_files:
        print(f"Aucun fichier PDF trouvé dans '{source_dir}'.")
        return

    print(f"=== Début de l'extraction par lot ({len(pdf_files)} PDFs trouvés) ===")
    os.makedirs(output_dir, exist_ok=True)

    for pdf_file in pdf_files:
        pdf_path = os.path.join(source_dir, pdf_file)
        md_filename = sanitize_filename(pdf_file)
        output_path = os.path.join(output_dir, md_filename)
        extract_pdf_to_markdown(pdf_path, output_path)

    print(f"\nExtraction terminée ! Les fichiers extraits sont dans '{output_dir}'.")


if __name__ == "__main__":
    extract_all_pdfs()
