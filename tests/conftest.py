"""Test configuration and fixtures"""

import pytest
from pathlib import Path
from src.config import Config

@pytest.fixture
def test_config():
    """Provide test configuration"""
    return Config(
        environment="test",
        debug=True,
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        vector_store_type="faiss",
    )

@pytest.fixture
def test_data_dir(tmp_path):
    """Create temporary test data directory"""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    return str(data_dir)
