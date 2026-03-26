"""WordlistManager — manages system and custom wordlists"""
import os
import logging
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Common system wordlist paths
SYSTEM_WORDLIST_PATHS = {
    "rockyou":        "/usr/share/wordlists/rockyou.txt",
    "rockyou_gz":     "/usr/share/wordlists/rockyou.txt.gz",
    "dirb_common":    "/usr/share/wordlists/dirb/common.txt",
    "dirb_big":       "/usr/share/wordlists/dirb/big.txt",
    "dirbuster_med":  "/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt",
    "dirbuster_sml":  "/usr/share/wordlists/dirbuster/directory-list-2.3-small.txt",
    "fasttrack":      "/usr/share/wordlists/fasttrack.txt",
    "seclists_pass":  "/usr/share/seclists/Passwords/Common-Credentials/10-million-password-list-top-1000.txt",
    "seclists_user":  "/usr/share/seclists/Usernames/top-usernames-shortlist.txt",
    "unix_passwords": "/usr/share/wordlists/metasploit/unix_passwords.txt",
}

# Default directory for custom wordlists
CUSTOM_WORDLIST_DIR = os.environ.get("CUSTOM_WORDLIST_DIR", "/tmp/wordlists")


class WordlistManager:
    """Manages system wordlists and custom wordlist creation."""

    def __init__(self, custom_dir: Optional[str] = None):
        self.custom_dir = Path(custom_dir or CUSTOM_WORDLIST_DIR)
        self._ensure_custom_dir()

    def _ensure_custom_dir(self) -> None:
        try:
            self.custom_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.warning("Cannot create custom wordlist directory %s: %s", self.custom_dir, exc)

    # ------------------------------------------------------------------
    # System wordlists
    # ------------------------------------------------------------------

    def list_system_wordlists(self) -> List[Dict[str, str]]:
        """Return all known system wordlists with availability status."""
        result = []
        for name, path in SYSTEM_WORDLIST_PATHS.items():
            result.append({
                "name": name,
                "path": path,
                "available": os.path.isfile(path),
                "type": "system",
            })
        return result

    def get_system_path(self, name: str) -> Optional[str]:
        """Return the path for a named system wordlist if it exists."""
        path = SYSTEM_WORDLIST_PATHS.get(name)
        if path and os.path.isfile(path):
            return path
        return None

    # ------------------------------------------------------------------
    # Custom wordlists
    # ------------------------------------------------------------------

    def list_custom_wordlists(self) -> List[Dict[str, str]]:
        """Return all custom wordlists in the custom directory."""
        result = []
        if not self.custom_dir.exists():
            return result
        for f in sorted(self.custom_dir.iterdir()):
            if f.is_file():
                try:
                    size = f.stat().st_size
                    with open(f, "r", errors="ignore") as fh:
                        line_count = sum(1 for _ in fh)
                except OSError:
                    size = 0
                    line_count = 0
                result.append({
                    "name": f.name,
                    "path": str(f),
                    "size_bytes": size,
                    "word_count": line_count,
                    "type": "custom",
                })
        return result

    def save_custom_wordlist(self, name: str, words: List[str]) -> str:
        """Save a list of words as a custom wordlist. Returns file path."""
        if not name.endswith(".txt"):
            name = name + ".txt"
        # Sanitize filename
        safe_name = "".join(c for c in name if c.isalnum() or c in "_-.")
        if not safe_name:
            safe_name = "custom.txt"
        path = self.custom_dir / safe_name
        with open(path, "w") as fh:
            fh.write("\n".join(words))
        logger.info("Saved custom wordlist %s (%d words)", path, len(words))
        return str(path)

    def save_cewl_output(self, name: str, cewl_words: List[str]) -> str:
        """Convenience wrapper for saving CeWL-generated wordlists."""
        return self.save_custom_wordlist(f"cewl_{name}", cewl_words)

    def delete_custom_wordlist(self, name: str) -> bool:
        """Delete a custom wordlist by filename. Returns True if deleted."""
        if not name.endswith(".txt"):
            name = name + ".txt"
        path = self.custom_dir / name
        if path.exists() and path.parent == self.custom_dir:
            path.unlink()
            return True
        return False

    # ------------------------------------------------------------------
    # Combined listing
    # ------------------------------------------------------------------

    def list_all(self) -> Dict[str, List[Dict]]:
        """Return both system and custom wordlists."""
        return {
            "system": self.list_system_wordlists(),
            "custom": self.list_custom_wordlists(),
        }
