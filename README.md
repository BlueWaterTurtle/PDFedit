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

This editor currently supports **text insertion overlays** (adding text to a page).  
It does not yet modify existing PDF text objects in-place.
