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
- **Select existing text blocks** by enabling Select Mode and clicking on them
- **Edit selected text in-place** via the text entry field and "Apply Edit" button
- **Delete selected text elements** using the "Delete Selected" button or the Delete key
- **Move selected text** to a new position with Shift+click while in Select Mode
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

This editor supports **text insertion overlays** (adding new text to a page) and **editing existing PDF text elements** (selecting, modifying, moving, and deleting text blocks using PyMuPDF redaction).
