# TODO - PDF Fake News Prediction Fix

- [ ] Scan current prediction workflow to identify why PDFs raise "File is corrupted."
- [ ] Modify existing PDF upload/prediction logic only (no new routes/blueprints/files).
- [ ] Ensure PDFs are read as bytes/files saved to disk (no file.read().decode("utf-8")).
- [ ] Use `utils/pdf_utils.extract_text_from_pdf` directly.
- [ ] Add exception handling + logging so real PDF errors are visible.
- [ ] If extracted text is empty (selectable text missing), show exact message required.
- [ ] If PDF parser fails (damaged/unreadable), show "File is corrupted." only then.
- [ ] Ensure TXT/CSV/JSON paths remain unchanged.
- [ ] Validate by testing with multiple valid PDFs.

