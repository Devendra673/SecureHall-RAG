"""
Security module for SecureHall-RAG
Provides injection detection, safe prompting, and defense mechanisms
"""

from .injection_templates import (
    InjectionTemplate,
    SQLInjectionAttacks,
    PromptInjectionAttacks,
    LogicManipulationAttacks,
    InformationExtractionAttacks,
    ObfuscationAttacks,
    ChainingAttacks,
    get_all_attack_templates,
)

__all__ = [
    "InjectionTemplate",
    "SQLInjectionAttacks",
    "PromptInjectionAttacks",
    "LogicManipulationAttacks",
    "InformationExtractionAttacks",
    "ObfuscationAttacks",
    "ChainingAttacks",
    "get_all_attack_templates",
]
