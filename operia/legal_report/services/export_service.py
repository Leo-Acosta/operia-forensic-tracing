"""Compatibility shim for legacy legal_report export imports.

Export implementation now lives in operia.exports.report_exporters.
"""

from operia.exports.report_exporters import (
    export_docx,
    export_html,
    export_markdown,
    export_pdf,
    export_presentation_pdf,
)

__all__ = [
    "export_docx",
    "export_html",
    "export_markdown",
    "export_pdf",
    "export_presentation_pdf",
]
