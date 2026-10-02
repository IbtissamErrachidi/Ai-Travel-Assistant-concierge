"""Document cleaning module.
Cleans raw extracted Markdown files:
1. Replaces custom font icons / PUA unicode with semantic words:
   - \\ue938 -> 'Inclus'
   - \\ue93a -> 'Non inclus'
   - \\ue907 -> 'Autorisé'
2. Strips residual UI icons and emoji artifacts (\\ue000-\\uf8ff).
3. Removes web boilerplate (navigation headers, search bars, social media links, copyright footers).
4. De-duplicates false single-cell layout tables and broken text echoes.
5. Normalizes whitespace and structure for optimal RAG chunking.
"""

import os
import re
from typing import Optional

EXTRACTED_MD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "extracted_md"))

# Semantic icon mappings
SEMANTIC_REPLACEMENTS = {
    "\ue938": "Inclus",
    "\ue93a": "Non inclus",
    "\ue907": "Autorisé",
}

# Web noise patterns to strip out
WEB_BOILERPLATE_PATTERNS = [
    r"Rechercher sur notre site web.*?(?=\n|$)",
    r"Follow us on.*?(?=\n|$)",
    r"Modes de paiement.*?(?=\n|$)",
    r"Site Corporate.*?Plan du site.*?Nos partenaires.*?(?=\n|$)",
    r"Plan du site Conditions générales Nos partenaires.*?(?=\n|$)",
    r"© \d{4} Royal Air Maroc\. Tous les droits réservés.*?(?=\n|$)",
    r"Book a flight.*?(?=\n|$)",
    r"^\s*(?:Explorer|Expérience|Information|Safar Flyer|Destinations|Aide)\s*$",
]


def replace_semantic_icons(text: str) -> str:
    """Replace font icons with clear semantic text (Inclus, Non inclus, Autorisé)."""
    for char, replacement in SEMANTIC_REPLACEMENTS.items():
        text = text.replace(char, replacement)
    
    # Strip any remaining Private Use Area characters
    text = re.sub(r"[\ue000-\uf8ff]", "", text)
    return text


def clean_web_boilerplate(text: str) -> str:
    """Remove web navigation menus, social media footers, and tracking widgets."""
    for pattern in WEB_BOILERPLATE_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.MULTILINE | re.IGNORECASE)
    return text


def clean_broken_table_echoes(text: str) -> str:
    """In Conditions Tarifaires, pdfplumber extracts the table in markdown grid,
    and then echoes the same table content broken across lines under 'Texte extrait'.
    This removes that scrambled duplicate section.
    """
    # Pattern matching the scrambled page 2 text echo in conditions_tarifaires.md
    scrambled_echo = re.compile(
        r"###\s*Texte extrait\s*:\s*\n+Des tarifs adaptés pour accompagner votre voyage\n+Eco Business Business.*?(?=\n{2,}Conditions de changement|$)",
        re.DOTALL,
    )
    text = scrambled_echo.sub("### Texte extrait :\n\n", text)
    return text


def clean_single_cell_layout_tables(text: str) -> str:
    """Convert single-cell layout tables (| Content |) into normal text paragraphs."""
    lines = text.split("\n")
    cleaned_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Detect single-cell markdown table block:
        # | Header |
        # | --- |
        # | Long text... |
        if (
            line.startswith("|")
            and line.endswith("|")
            and line.count("|") == 2
            and i + 2 < len(lines)
            and re.match(r"^\|\s*---\s*\|$", lines[i + 1].strip())
            and lines[i + 2].startswith("|")
            and lines[i + 2].endswith("|")
            and lines[i + 2].count("|") == 2
        ):
            header = line.strip("|").strip()
            content = lines[i + 2].strip("|").strip()
            if header:
                cleaned_lines.append(f"### {header}\n")
            cleaned_lines.append(content)
            i += 3
            continue

        cleaned_lines.append(line)
        i += 1

    return "\n".join(cleaned_lines)


def normalize_whitespace(text: str) -> str:
    """Normalize line breaks and trailing spaces."""
    # Remove trailing whitespace from each line
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)
    # Collapse 3 or more empty lines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def clean_document_content(content: str) -> str:
    """Apply the complete cleaning pipeline to document markdown content."""
    text = replace_semantic_icons(content)
    text = clean_broken_table_echoes(text)
    text = clean_web_boilerplate(text)
    text = clean_single_cell_layout_tables(text)
    text = normalize_whitespace(text)
    return text


def clean_file(file_path: str, output_path: Optional[str] = None) -> None:
    """Clean a single markdown file and save the result."""
    if output_path is None:
        output_path = file_path

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    cleaned_content = clean_document_content(content)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(cleaned_content)

    print(f"Nettoyé : {os.path.basename(file_path)} -> {os.path.basename(output_path)}")


def clean_all_extracted_docs(docs_dir: str = EXTRACTED_MD_DIR) -> None:
    """Batch clean all markdown files in the extracted_md directory."""
    if not os.path.exists(docs_dir):
        print(f"Le dossier '{docs_dir}' n'existe pas.")
        return

    md_files = [f for f in os.listdir(docs_dir) if f.lower().endswith(".md")]
    if not md_files:
        print(f"Aucun fichier markdown trouvé dans '{docs_dir}'.")
        return

    print(f"=== Nettoyage de {len(md_files)} documents dans '{docs_dir}' ===")
    for md_file in md_files:
        path = os.path.join(docs_dir, md_file)
        clean_file(path)

    print("\nNettoyage terminé avec succès !")


if __name__ == "__main__":
    clean_all_extracted_docs()
