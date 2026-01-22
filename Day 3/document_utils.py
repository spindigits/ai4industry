"""
Document Loading Utilities
"""
from typing import List, Dict
from pathlib import Path
import pypdf
import docx
import json
import csv


def load_pdf(file_path: str) -> str:
    """Charge un fichier PDF"""
    try:
        reader = pypdf.PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        raise Exception(f"Erreur lecture PDF: {str(e)}")


def load_docx(file_path: str) -> str:
    """Charge un fichier DOCX"""
    try:
        doc = docx.Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text
    except Exception as e:
        raise Exception(f"Erreur lecture DOCX: {str(e)}")


def load_txt(file_path: str) -> str:
    """Charge un fichier TXT"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        raise Exception(f"Erreur lecture TXT: {str(e)}")


def load_json(file_path: str) -> str:
    """Charge un fichier JSON et le convertit en texte"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        raise Exception(f"Erreur lecture JSON: {str(e)}")


def load_csv(file_path: str) -> str:
    """Charge un fichier CSV et le convertit en texte"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Convert to readable text
        text_lines = []
        for row in rows:
            line = ", ".join([f"{k}: {v}" for k, v in row.items()])
            text_lines.append(line)
        
        return "\n".join(text_lines)
    except Exception as e:
        raise Exception(f"Erreur lecture CSV: {str(e)}")


def load_document(file_path: str) -> str:
    """
    Charge un document selon son extension
    
    Args:
        file_path: Chemin du fichier
        
    Returns:
        Contenu du document en texte
    """
    file_path = Path(file_path)
    extension = file_path.suffix.lower()
    
    loaders = {
        '.pdf': load_pdf,
        '.docx': load_docx,
        '.doc': load_docx,
        '.txt': load_txt,
        '.json': load_json,
        '.csv': load_csv,
    }
    
    loader = loaders.get(extension)
    if not loader:
        raise ValueError(f"Format non supporté: {extension}")
    
    return loader(str(file_path))


def split_into_chunks(text: str, text_splitter) -> List[Dict]:
    """
    Split text into chunks
    
    Args:
        text: Texte à découper
        text_splitter: LangChain text splitter
        
    Returns:
        Liste de documents avec text et metadata
    """
    chunks = text_splitter.split_text(text)
    
    documents = []
    for chunk in chunks:
        documents.append({
            'text': chunk,
            'metadata': {}
        })
    
    return documents
