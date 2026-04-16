import re
from docx import Document


def extract_paragraphs(doc) -> list[str]:
    return [p.text.strip() for p in doc.paragraphs if p.text.strip()]


def extract_tables(doc) -> list[str]:
    rows = []
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                rows.append(" | ".join(cells))
    return rows


def extract_headers_footers(doc) -> list[str]:
    texts = []
    for section in doc.sections:
        for para in section.header.paragraphs:
            if para.text.strip():
                texts.append(para.text.strip())
        for para in section.footer.paragraphs:
            if para.text.strip():
                texts.append(para.text.strip())
    return texts


def docx_to_text(file_path: str) -> str:
    try:
        doc = Document(file_path)
    except Exception:
        return ""

    content = (
        extract_paragraphs(doc)
        + extract_tables(doc)
        + extract_headers_footers(doc)
    )

    lines = [l.strip() for l in "\n".join(content).split("\n") if l.strip()]
    return "\n".join(lines)
