"""Tool definitions — auto-registers tools with ToolRegistry on import"""
from app.core.tool_definitions import (  # noqa: F401
    nmap_tool,
    nikto_tool,
    gobuster_tool,
    hydra_tool,
    john_tool,
    medusa_tool,
    cewl_tool,
    wpscan_tool,
    # OSINT tools
    shodan_tool,
    theharvester_tool,
    whois_tool,
    hunter_io_tool,
    passive_dns_tool,
    # Exploitation tools
    sqlmap_tool,
    metasploit_tool,
    burpsuite_tool,
    gophish_tool,
    # Post-exploitation tools
    mimikatz_tool,
    empire_tool,
    lateral_movement_tool,
)
