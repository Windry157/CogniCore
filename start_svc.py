"""Start CogniCore service with remote Ollama"""
import os, sys

APP_DIR = os.path.join(os.path.dirname(__file__), "cognicore")
sys.path.insert(0, APP_DIR)
os.environ["CONFIG_PATH"] = os.path.join(APP_DIR, "config.yaml")
os.environ["LLM_OLLAMA_BASE_URL"] = "http://192.168.3.105:11434"

# Import and patch Config singleton BEFORE uvicorn imports app module.
# __init__.py re-exports `config` (the instance), which shadows the
# submodule name, so we reach it via the package.
import src.core.config
cfg = src.core.config.config
cfg.llm.ollama_base_url = "http://192.168.3.105:11434"

import uvicorn
uvicorn.run("app:app", host="0.0.0.0", port=8002, log_level="info")
