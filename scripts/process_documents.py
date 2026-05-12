"""Script to process documents"""

import argparse
import logging
from pathlib import Path
from src.data import DocumentLoaderFactory
from src.config import config
from src.utils import setup_logging, ensure_directories, get_file_paths

setup_logging()
logger = logging.getLogger(__name__)

def process_documents(input_dir: str, output_dir: str, chunk_size: int = 512):
    """Process documents from input directory"""
    
    # Ensure output directory exists
    ensure_directories([output_dir])
    
    # Get all documents
    doc_files = get_file_paths(
        input_dir,
        extensions=['*.pdf', '*.docx', '*.doc', '*.txt']
    )
    
    logger.info(f"Found {len(doc_files)} documents to process")
    
    processed_count = 0
    for file_path in doc_files:
        try:
            logger.info(f"Processing: {file_path}")
            
            # Load document
            text = DocumentLoaderFactory.load_document(file_path)
            
            # Save processed document
            output_path = Path(output_dir) / f"{Path(file_path).stem}.txt"
            output_path.write_text(text)
            
            logger.info(f"Saved: {output_path}")
            processed_count += 1
        
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
    
    logger.info(f"Processed {processed_count}/{len(doc_files)} documents")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process documents")
    parser.add_argument("--input", default=config.data_dir, help="Input directory")
    parser.add_argument("--output", default=config.processed_data_dir, help="Output directory")
    parser.add_argument("--chunk-size", type=int, default=512, help="Chunk size")
    
    args = parser.parse_args()
    
    process_documents(args.input, args.output, args.chunk_size)
