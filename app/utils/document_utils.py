from pathlib import Path
from typing import List, Dict, Any
import logging
from llama_index.core import Document
from llama_index.readers.file import (
    PyMuPDFReader,
    UnstructuredReader,
    PagedCSVReader
)

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Utility class for processing different document types"""
    
    def __init__(self):
        self.pdf_reader = PyMuPDFReader()
        self.unstructured_reader = UnstructuredReader()
        self.csv_reader = PagedCSVReader()
    
    def process_pdf(self, file_path: Path) -> List[Document]:
        """Process PDF files"""
        try:
            return self.pdf_reader.load_data(file_path=file_path, metadata=True)
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {e}")
            return []
    
    def process_unstructured(self, file_path: Path) -> List[Document]:
        """Process various file types using Unstructured"""
        try:
            return self.unstructured_reader.load_data(
                unstructured_kwargs={"filename": str(file_path)}
            )
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            return []
    
    def process_csv(self, file_path: Path) -> List[Document]:
        """Process CSV files"""
        try:
            return self.csv_reader.load_data(file=file_path)
        except Exception as e:
            logger.error(f"Error processing CSV {file_path}: {e}")
            return []
    
    def process_directory(self, directory_path: Path) -> List[Document]:
        """Process all supported files in a directory"""
        documents = []
        
        for file_path in directory_path.rglob("*"):
            if file_path.is_file():
                suffix = file_path.suffix.lower()
                
                if suffix == ".pdf":
                    documents.extend(self.process_pdf(file_path))
                elif suffix == ".csv":
                    documents.extend(self.process_csv(file_path))
                elif suffix in [".txt", ".md", ".html", ".docx"]:
                    documents.extend(self.process_unstructured(file_path))
        
        return documents