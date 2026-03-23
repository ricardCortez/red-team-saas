"""Tool Execution Types and Enums"""
from enum import Enum


class ExecutionMode(str, Enum):
    CORE_DIRECT = "core_direct"    # OPCIÓN A: Direct wrapper
    GENERIC_CLI = "generic_cli"    # OPCIÓN B/C: Generic executor
    PLUGIN = "plugin"              # OPCIÓN B: Plugin system
    API_GATEWAY = "api_gateway"    # OPCIÓN B/C: API integration


class ArchitectureOption(str, Enum):
    A = "A"  # MVP Rápido (25 core tools)
    B = "B"  # Completo (175+ tools + plugins)
    C = "C"  # Híbrida (100+ tools)


class ToolCategory(str, Enum):
    OSINT = "osint"
    ENUMERATION = "enumeration"
    BRUTE_FORCE = "brute_force"
    PHISHING = "phishing"
    EXPLOITATION = "exploitation"
    POST_EXPLOITATION = "post_exploitation"
    CRYPTOGRAPHY = "cryptography"
    NETWORK = "network"
    MALWARE = "malware"
    CUSTOM = "custom"  # Para plugins


# Mapping de herramientas por opción
TOOLS_BY_OPTION = {
    "A": {
        "total": 25,
        "categories": {
            "osint": 5,
            "enumeration": 3,
            "brute_force": 5,
            "phishing": 2,
            "exploitation": 3,
            "post_exploitation": 2,
        },
    },
    "C": {
        "total": 100,
        "categories": {
            "osint": 20,
            "enumeration": 25,
            "brute_force": 10,
            "phishing": 5,
            "exploitation": 20,
            "post_exploitation": 10,
            "cryptography": 5,
            "network": 5,
        },
    },
    "B": {
        "total": 175,
        "categories": {
            "osint": 30,
            "enumeration": 40,
            "brute_force": 15,
            "phishing": 10,
            "exploitation": 30,
            "post_exploitation": 20,
            "cryptography": 15,
            "network": 15,
        },
    },
}
