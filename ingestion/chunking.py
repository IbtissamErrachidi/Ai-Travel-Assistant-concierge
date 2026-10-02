"""Chunking module for Travel Assistant RAG.
Splits extracted Markdown documents into semantically coherent chunks,
preserving Markdown table structures and headers while filtering noise
and merging small consecutive text chunks.
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from transformers import AutoTokenizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chunker")

# Paramètres de découpage (en tokens)
CHUNK_SIZE_TOKENS = 512
CHUNK_OVERLAP_TOKENS = 20

# Structure des répertoires
BASE_DIR = Path(__file__).resolve().parents[1]
EXTRACTED_MD_DIR = BASE_DIR / "extracted_md"
CHUNKS_DIR = BASE_DIR / "chunks"

HEADERS_TO_SPLIT_ON = [
    ("#", "document"),
    ("###", "section"),
]

# Charger le tokenizer du modèle d'embedding (intfloat/multilingual-e5-base)
tokenizer = AutoTokenizer.from_pretrained("intfloat/multilingual-e5-base")


def count_tokens(text: str) -> int:
    """Compte le nombre exact de tokens via le tokenizer E5."""
    return len(tokenizer.encode(text, add_special_tokens=False))


def is_noisy_chunk(text: str) -> bool:
    """Détecte et filtre le bruit de mise en page, balises vides et artefacts d'OCR/conversion."""
    clean_text = text.strip()

    # 1. Chunks extrêmement courts sans substance
    if len(clean_text) < 15:
        return True

    # 2. Scories de conversion Markdown courantes
    ignored_patterns = [
        r"^###?\s*Tableaux? détectés?\s*:?$",
        r"^###?\s*Texte extrait\s*:?$",
        r"^##?\s*PAGE\s*\d+\s*$",
        r"^\d+\s*$",  
    ]
    for pattern in ignored_patterns:
        if re.match(pattern, clean_text, re.IGNORECASE):
            return True

    # 3. Chunks ne contenant que des titres Markdown sans contenu réel
    lines = [l.strip() for l in clean_text.splitlines() if l.strip()]
    if all(l.startswith("#") for l in lines):
        return True

    return False


def extract_tables_and_text(text: str) -> List[Dict[str, str]]:
    """Isole les tableaux Markdown du texte fluide pour éviter qu'ils ne soient brisés."""
    blocks = []
    table_pattern = re.compile(r"(\|.+\|[\s\S]*?)(?=\n[^|]|\Z)", re.MULTILINE)

    last_end = 0
    for match in table_pattern.finditer(text):
        start, end = match.start(), match.end()

        # Bloc de texte avant le tableau
        if start > last_end:
            pre_text = text[last_end:start].strip()
            if pre_text:
                blocks.append({"type": "text", "content": pre_text})

        # Bloc tableau
        table_content = match.group(0).strip()
        if table_content:
            blocks.append({"type": "table", "content": table_content})

        last_end = end

    # Bloc de texte restant après le dernier tableau
    if last_end < len(text):
        remaining = text[last_end:].strip()
        if remaining:
            blocks.append({"type": "text", "content": remaining})

    return blocks if blocks else [{"type": "text", "content": text}]


def get_document_topic(source_name: str) -> str:
    """Génère un titre thématique lisible à partir du nom du fichier."""
    return Path(source_name).stem.replace("_", " ").title()


def split_large_table(
    table_content: str,
    source: str,
    chunk_idx: int,
    metadata: Dict[str, Any],
    table_title: str,
) -> List[Dict[str, Any]]:
    """Découpe un tableau dépassant la limite de tokens en dupliquant ses en-têtes."""
    lines = table_content.strip().splitlines()

    if len(lines) < 3:
        return []

    header_line = lines[0]
    separator_line = lines[1]
    data_rows = lines[2:]

    header_block = f"{header_line}\n{separator_line}\n"
    header_tokens = count_tokens(header_block)

    sub_chunks_content = []
    current_rows = []
    current_tokens = header_tokens

    for row in data_rows:
        if not row.strip():
            continue
        row_tokens = count_tokens(row)

        if current_tokens + row_tokens > CHUNK_SIZE_TOKENS and current_rows:
            sub_table = header_block + "\n".join(current_rows)
            sub_chunks_content.append(sub_table)
            current_rows = []
            current_tokens = header_tokens

        current_rows.append(row)
        current_tokens += row_tokens

    if current_rows:
        sub_table = header_block + "\n".join(current_rows)
        sub_chunks_content.append(sub_table)

    total_parts = len(sub_chunks_content)
    result = []
    for i, content in enumerate(sub_chunks_content):
        chunk = {
            "chunk_id": f"{Path(source).stem}_chunk_{chunk_idx + i}",
            "text": content.strip(),
            "source": source,
            "metadata": {
                **metadata,
                "block_type": "table",
                "table_title": table_title,
                "table_part": i + 1,
                "table_total_parts": total_parts,
            },
            "type": "table",
        }
        result.append(chunk)

    return result


def merge_text_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Fusionne les petits chunks de texte consécutifs tant que la taille combinée ne dépasse pas 512 tokens.
    Si l'ajout du nouveau chunk dépasse 512 tokens, il N'EST PAS fusionné et démarre un nouveau chunk.
    """
    if not chunks:
        return []

    merged_chunks = []
    buffer_text = []
    first_chunk = None

    for chunk in chunks:
        # Si c'est un tableau, on ferme le buffer de texte et on ajoute le tableau séparément
        if chunk.get("type") == "table":
            if buffer_text:
                merged_chunks.append({
                    "chunk_id": "",
                    "text": "\n".join(buffer_text).strip(),
                    "source": first_chunk["source"],
                    "metadata": first_chunk["metadata"],
                    "type": "text",
                })
                buffer_text = []
                first_chunk = None
            merged_chunks.append(chunk)
            continue

        text_to_add = chunk["text"]

        if not buffer_text:
            buffer_text = [text_to_add]
            first_chunk = chunk
        else:
            # Tester la taille combinée réelle si on ajoutait ce nouveau chunk
            candidate_text = "\n".join(buffer_text + [text_to_add]).strip()
            candidate_tokens = count_tokens(candidate_text)

            # Si le merge reste sous ou égal à 512 tokens, on accepte la fusion
            if candidate_tokens <= CHUNK_SIZE_TOKENS:
                buffer_text.append(text_to_add)
            else:
                # Sinon ON NE MERGE PAS ce chunk : on finalise le buffer actuel
                merged_chunks.append({
                    "chunk_id": "",
                    "text": "\n".join(buffer_text).strip(),
                    "source": first_chunk["source"],
                    "metadata": first_chunk["metadata"],
                    "type": "text",
                })
                # Et ce chunk qui a tenté le merge devient le premier élément du nouveau buffer
                buffer_text = [text_to_add]
                first_chunk = chunk

    # Finaliser le dernier buffer à la fin du document
    if buffer_text:
        merged_chunks.append({
            "chunk_id": "",
            "text": "\n".join(buffer_text).strip(),
            "source": first_chunk["source"],
            "metadata": first_chunk["metadata"],
            "type": "text",
        })

    # Re-numérotation propre des IDs de chunks
    for idx, c in enumerate(merged_chunks):
        stem = Path(c["source"]).stem
        c["chunk_id"] = f"{stem}_chunk_{idx}"

    return merged_chunks


def chunk_markdown_file(md_path: Path) -> List[Dict[str, Any]]:
    """Découpe un fichier Markdown en chunks optimisés pour le RAG avec fusion sous la limite de 512 tokens."""
    text = md_path.read_text(encoding="utf-8")
    source_name = md_path.name
    doc_topic = get_document_topic(source_name)

    # 1. Découpage hiérarchique par titres Markdown (sans couper sur les numéros de page)
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADERS_TO_SPLIT_ON,
        strip_headers=False,
    )
    header_chunks = markdown_splitter.split_text(text)

    # 2. Découpage textuel récursif au niveau des tokens
    text_splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
        tokenizer,
        chunk_size=CHUNK_SIZE_TOKENS,
        chunk_overlap=CHUNK_OVERLAP_TOKENS,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    intermediate_chunks = []
    chunk_idx = 0

    for header_chunk in header_chunks:
        blocks = extract_tables_and_text(header_chunk.page_content)

        for block in blocks:
            if block["type"] == "table":
                content = f"Tableau ({doc_topic}) :\n{block['content'].strip()}"
                tokens_count = count_tokens(content)

                if tokens_count <= CHUNK_SIZE_TOKENS:
                    chunk = {
                        "chunk_id": f"{md_path.stem}_chunk_{chunk_idx}",
                        "text": content,
                        "source": source_name,
                        "metadata": {
                            **header_chunk.metadata,
                            "block_type": "table",
                            "table_title": doc_topic,
                            "table_part": 1,
                            "table_total_parts": 1,
                        },
                        "type": "table",
                    }
                    intermediate_chunks.append(chunk)
                    chunk_idx += 1
                else:
                    sub_chunks = split_large_table(
                        table_content=block["content"],
                        source=source_name,
                        chunk_idx=chunk_idx,
                        metadata=header_chunk.metadata,
                        table_title=doc_topic,
                    )
                    intermediate_chunks.extend(sub_chunks)
                    chunk_idx += len(sub_chunks)

            else:
                sub_chunks = text_splitter.split_text(block["content"])
                for sub_chunk in sub_chunks:
                    clean_chunk = sub_chunk.strip()

                    # Filtrage du bruit et des en-têtes isolés
                    if is_noisy_chunk(clean_chunk):
                        continue

                    chunk = {
                        "chunk_id": f"{md_path.stem}_chunk_{chunk_idx}",
                        "text": clean_chunk,
                        "source": source_name,
                        "metadata": {
                            **header_chunk.metadata,
                            "doc_topic": doc_topic,
                            "block_type": "text",
                        },
                        "type": "text",
                    }
                    intermediate_chunks.append(chunk)
                    chunk_idx += 1

    # 3. Fusion dynamique des sous-chunks de texte (stricte limite à <= 512 tokens)
    final_chunks = merge_text_chunks(intermediate_chunks)

    logger.info(f"{len(final_chunks)} chunks valides générés pour {source_name}")
    return final_chunks


def process_all_extracted_docs() -> None:
    """Traite l'ensemble des fichiers Markdown du répertoire source."""
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
    md_files = list(EXTRACTED_MD_DIR.glob("*.md"))

    if not md_files:
        logger.warning(f"Aucun fichier Markdown trouvé dans {EXTRACTED_MD_DIR}")
        return

    for md_file in md_files:
        chunks = chunk_markdown_file(md_file)

        # Sauvegarde individuelle
        output_file = CHUNKS_DIR / f"{md_file.stem}_chunks.json"
        output_file.write_text(
            json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    logger.info(f"Chunking terminé ! Les fichiers JSON ont été enregistrés dans {CHUNKS_DIR}.")


if __name__ == "__main__":
    process_all_extracted_docs()