"""Tests for document loading"""

import pytest
from pathlib import Path
from src.data import (
    DocumentLoaderFactory,
    PDFLoader,
    TextLoader,
    WordLoader
)

class TestDocumentLoaderFactory:
    """Test document loader factory"""
    
    def test_get_pdf_loader(self):
        """Test getting PDF loader"""
        loader = DocumentLoaderFactory.get_loader("test.pdf")
        assert isinstance(loader, PDFLoader)
    
    def test_get_text_loader(self):
        """Test getting text loader"""
        loader = DocumentLoaderFactory.get_loader("test.txt")
        assert isinstance(loader, TextLoader)
    
    def test_unsupported_format(self):
        """Test unsupported file format"""
        with pytest.raises(ValueError):
            DocumentLoaderFactory.get_loader("test.xyz")

class TestTextLoader:
    """Test text loader"""
    
    def test_load_text_file(self, tmp_path):
        """Test loading plain text file"""
        test_file = tmp_path / "test.txt"
        test_content = "This is a test document."
        test_file.write_text(test_content)
        
        loader = TextLoader()
        document = loader.load(str(test_file))
        assert document.text == test_content
        assert document.metadata["file_name"] == "test.txt"
    
    def test_validate_valid_file(self, tmp_path):
        """Test validation of valid file"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        
        loader = TextLoader()
        assert loader.validate(str(test_file)) is True
