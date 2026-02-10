import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

COUNCIL_DIR = Path(__file__).resolve().parents[3].parent.parent / "scripts" / "llm-council"


def _ensure_council_path() -> None:
    council_str = str(COUNCIL_DIR)
    if council_str not in sys.path:
        sys.path.insert(0, council_str)


class CouncilWrapper:
    def __init__(self) -> None:
        self._council = None

    def _get_council(self):
        if self._council is None:
            _ensure_council_path()
            try:
                from council import LLMCouncil, CouncilConfig
                config_path = COUNCIL_DIR / "config.yaml"
                if config_path.exists():
                    config = CouncilConfig.from_yaml(config_path)
                    self._council = LLMCouncil(config)
                else:
                    logger.warning("Council config not found at %s", config_path)
            except ImportError:
                logger.warning("LLM Council not available (import failed)")
            except Exception:
                logger.exception("Failed to initialize LLM Council")
        return self._council

    async def query(
        self, prompt: str, mode: str = "full"
    ) -> Optional[dict[str, Any]]:
        council = self._get_council()
        if not council:
            return None
        try:
            result = await council.query(prompt, mode=mode)
            return result
        except Exception:
            logger.exception("Council query failed")
            return None

    @property
    def available(self) -> bool:
        return self._get_council() is not None


council_wrapper = CouncilWrapper()
