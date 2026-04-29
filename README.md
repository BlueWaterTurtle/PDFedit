# PDFedit

A lightweight, portable PDF editor desktop app with:

- **OCR** (extract text from scanned pages)
- **Basic editing** (insert new text on pages)
- **Cross-platform UI** using Python + Tkinter

## Features

- Open a PDF and preview pages
- Navigate pages (Previous/Next)
- OCR current page
- OCR entire document and export as `.txt`
- Insert text on a page by entering text and clicking where to place it
- **Select existing elements** by enabling Select Mode and clicking on them:
  - 🔵 **Text spans** (including bullets and special characters) — highlighted in blue
  - 🟢 **Vector drawings** (lines, rectangles, shapes) — highlighted in green
  - 🟠 **Embedded images** — highlighted in orange
- **Edit selected text in-place** via the text entry field and "Apply Edit" button (text spans only)
- **Delete selected text elements or images** using the "Delete Selected" button or the Delete key
- **Move selected text** to a new position with Shift+click while in Select Mode
- **Non-destructive editing** — text removal uses surgical content-stream editing instead of redaction, so images, graphics, and other text underneath are never destroyed
- Undo last operation (Ctrl+Z or Undo button)
- Save edited PDF to a new file

## Requirements

- Python 3.10+
- Tesseract OCR engine installed on your OS

Python packages:

- PyMuPDF
- Pillow
- pytesseract

## Install

```bash
python -m pip install -r requirements.txt
```

Install Tesseract:

- **Ubuntu/Debian**: `sudo apt-get install tesseract-ocr`
- **macOS (Homebrew)**: `brew install tesseract`
- **Windows**: install Tesseract from the official installer and ensure it is in `PATH`

## Run

```bash
python app.py
```

## Notes on editing

This editor supports **text insertion overlays** (adding new text to a page) and **editing existing PDF elements** (selecting, modifying, moving, and deleting text spans, vector drawings, and images).

- **Non-destructive text editing**: instead of using `apply_redactions()` (which permanently whites out a bounding-box area, destroying any underlying content), the editor directly manipulates the page content stream to remove only the specific text operators for the target span. Other content — images, graphics, and surrounding text — is unaffected. *Note: this approach works reliably for text using standard Latin-1 / PDFDocEncoding. Text stored with complex custom encodings, font subsets, or in encrypted PDFs may not be matched and will show a warning instead.*
- **Span-level selection**: the editor uses `page.get_text("rawdict")` with `TEXT_PRESERVE_WHITESPACE` to detect individual text spans (including bullets and special/symbol characters) rather than working only at the block level.
- **Multi-element hit testing**: a single click in Select Mode checks text spans, then vector drawings (`page.get_drawings()`), then embedded images (`page.get_image_info()`) in that order, falling back to the nearest text span within ~1 inch if no element is directly under the cursor.
- The "Apply Edit" button is only active for text spans; editing drawings and images is out of scope.
- Test with PDFs that contain overlapping text, bullet lists, embedded images, and vector graphics.
