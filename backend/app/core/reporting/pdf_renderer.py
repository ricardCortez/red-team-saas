"""PDF renderer - converts HTML to PDF via WeasyPrint"""
from typing import Dict, Any

from app.core.reporting.base_renderer import BaseRenderer
from app.core.reporting.html_renderer import HTMLRenderer


class PDFRenderer(BaseRenderer):

    def render(self, data: Dict[str, Any], report) -> bytes:
        html_bytes = HTMLRenderer().render(data, report)
        try:
            from weasyprint import HTML  # noqa: PLC0415
            return HTML(string=html_bytes.decode("utf-8")).write_pdf()
        except ImportError:
            raise RuntimeError(
                "WeasyPrint is not installed. Run: pip install weasyprint"
            )
        except OSError as exc:
            raise RuntimeError(
                f"WeasyPrint native libraries not found (GTK/Pango required): {exc}"
            ) from exc

    def content_type(self) -> str:
        return "application/pdf"

    def extension(self) -> str:
        return "pdf"
