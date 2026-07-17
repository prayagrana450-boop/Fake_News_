from __future__ import annotations

from typing import Tuple


class PDFExtractionError(RuntimeError):
    """Raised when the PDF cannot be opened/parsed by either parser."""


class PDFEncryptedError(RuntimeError):
    """Raised when the PDF is encrypted and cannot be decrypted."""


def extract_text_from_pdf(file_path: str) -> Tuple[str, int]:
    """Extract text from a PDF.

    Primary: pdfplumber.
    Fallback: PyPDF2.

    Returns:
        (text, extracted_pages_nonblank)

    Behavior:
    - Ignores blank/whitespace-only pages.
    - Encrypted PDFs are handled best-effort; if decryption fails, an empty string is returned.
    - If parsing/opening fails (corrupted/unsupported), this function raises PDFExtractionError.
    """

    pdfplumber_error: Exception | None = None

    # --- Try pdfplumber (primary) ---
    try:
        import pdfplumber  # type: ignore

        full_text_parts: list[str] = []
        pages_nonblank = 0

        with pdfplumber.open(file_path) as pdf:
            # Extract from every page
            for page in pdf.pages:
                try:
                    txt = page.extract_text() or ""
                except Exception:
                    txt = ""

                if txt and txt.strip():
                    pages_nonblank += 1
                    full_text_parts.append(txt)

        extracted = "\n".join(full_text_parts).strip()
        return extracted, pages_nonblank

    except Exception as e:
        pdfplumber_error = e

    # --- Fallback to PyPDF2 ---
    try:
        import PyPDF2  # type: ignore

        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)

            # Best-effort for encrypted PDFs.
            if getattr(reader, "is_encrypted", False):
                try:
                    # Some PDFs may allow empty password.
                    reader.decrypt("")
                except Exception as e:
                    # Can't decrypt - treat as no readable text.
                    # Requirement says handle encrypted/invalid gracefully.
                    return "", 0

            full_text_parts: list[str] = []
            pages_nonblank = 0

            for page in reader.pages:
                try:
                    txt = page.extract_text() or ""
                except Exception:
                    txt = ""

                if txt and txt.strip():
                    pages_nonblank += 1
                    full_text_parts.append(txt)

            extracted = "\n".join(full_text_parts).strip()
            return extracted, pages_nonblank

    except Exception as e:
        raise PDFExtractionError(
            "Failed to parse the uploaded PDF with available extractors."
        ) from (pdfplumber_error or e)

