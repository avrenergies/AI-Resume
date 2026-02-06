from docx import Document

def docx_to_text(file_path):
    doc = Document(file_path)
    return "\n".join(p.text for p in doc.paragraphs)
