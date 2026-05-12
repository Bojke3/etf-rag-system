# Test to ensure structure is working

if __name__ == "__main__":
    try:
        from src.config import config
        from src.data import TextLoader
        from src.utils import setup_logging
        
        print("✓ All imports successful")
        print(f"✓ Config loaded: LLM={config.llm_type}")
        print(f"✓ Environment: {config.environment}")
        print("\n✅ Project structure is working!")
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)
