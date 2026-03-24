"""Generic output parsing utilities shared across tools"""
import re
from typing import List, Dict, Any


def extract_ips(text: str) -> List[str]:
    pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    return list(set(re.findall(pattern, text)))


def extract_urls(text: str) -> List[str]:
    pattern = r'https?://[^\s\'"<>]+'
    return list(set(re.findall(pattern, text)))


def extract_ports(text: str) -> List[Dict[str, Any]]:
    """Parse lines like '80/tcp open http' or '443/tcp open https'."""
    ports = []
    pattern = r'(\d+)/(tcp|udp)\s+(\w+)\s*(\S*)?'
    for match in re.finditer(pattern, text):
        ports.append({
            "port": match.group(1),
            "protocol": match.group(2),
            "state": match.group(3),
            "service": match.group(4) or "unknown",
        })
    return ports


def lines_containing(text: str, keyword: str) -> List[str]:
    return [line for line in text.splitlines() if keyword.lower() in line.lower()]
