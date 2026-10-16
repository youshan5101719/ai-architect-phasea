import logging
import sys
from pathlib import Path

_TRACE_FILE = Path(__file__).resolve().parent / "agent.trace.log"


def setup_agent_logging() -> None:
    file_logger = logging.getLogger("phasea.agent.file")
    if file_logger.handlers:
        return
    file_handler = logging.FileHandler(_TRACE_FILE, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(message)s"))
    file_logger.setLevel(logging.INFO)
    file_logger.addHandler(file_handler)
    file_logger.propagate = False


def agent_trace(message: str) -> None:
    """Always flush to stderr (same console as uvicorn) and append to agent.trace.log."""
    setup_agent_logging()
    sys.stderr.write(f"{message}\n")
    sys.stderr.flush()
    logging.getLogger("phasea.agent.file").info(message)


def trace_file_path() -> Path:
    return _TRACE_FILE
