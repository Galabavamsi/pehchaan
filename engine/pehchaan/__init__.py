"""Pehchaan: verify the person, not the voice.

Explainable fusion engine for voice-clone payment fraud (RAKSHAM Track 01).
"""
from .config import Config, default_config, load_config
from .fusion import Assessment, assess, should_ask_claim
from .signals import ALL_SIGNALS, FAMILIES, SIGNAL_FAMILY
from .trigger import TriggerInput, evaluate_trigger

__all__ = [
    "Assessment", "Config", "ALL_SIGNALS", "FAMILIES", "SIGNAL_FAMILY", "TriggerInput",
    "assess", "default_config", "evaluate_trigger", "load_config", "should_ask_claim",
]
__version__ = "0.1.0"
