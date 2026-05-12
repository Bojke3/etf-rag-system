"""Utility functions and helpers"""

from pathlib import Path
import logging
from typing import List

def setup_logging(log_dir: str = "./logs", log_level: str = "INFO"):
    """Setup logging configuration"""
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(Path(log_dir) / 'app.log'),
            logging.StreamHandler()
        ]
    )

def ensure_directories(paths: List[str]) -> None:
    """Ensure directories exist"""
    for path in paths:
        Path(path).mkdir(parents=True, exist_ok=True)

def get_file_paths(directory: str, extensions: List[str] = None) -> List[str]:
    """Get all file paths in directory with specific extensions"""
    path = Path(directory)
    if not path.exists():
        return []
    
    if extensions is None:
        extensions = ['*']
    
    files = []
    for ext in extensions:
        files.extend(path.glob(f'**/{ext}'))
    
    return sorted([str(f) for f in files if f.is_file()])
