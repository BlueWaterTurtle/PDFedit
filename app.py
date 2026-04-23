from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

import fitz  # PyMuPDF
import pytesseract
from PIL import Image, ImageTk


class PDFEditorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("PDFedit - OCR + Basic Editing")
        self.root.geometry("1200x800")

        self.doc: fitz.Document | None = None
        self.pdf_path: Path | None = None
        self.page_index = 0
        self.zoom = 1.5
        self.tk_img: ImageTk.PhotoImage | None = None
        self.current_pil_image: Image.Image | None = None
        self.page_scale_x = 1.0
        self.page_scale_y = 1.0
        self.insert_mode = False

        self._build_ui()

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill=tk.X)

        ttk.Button(top, text="Open PDF", command=self.open_pdf).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Save As", command=self.save_pdf).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Previous", command=self.prev_page).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Next", command=self.next_page).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="OCR Page", command=self.ocr_current_page).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="OCR All -> TXT", command=self.ocr_all_to_txt).pack(side=tk.LEFT, padx=4)

        self.page_label = ttk.Label(top, text="No file loaded")
        self.page_label.pack(side=tk.RIGHT, padx=4)

        mid = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        mid.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(mid, padding=8)
        right = ttk.Frame(mid, padding=8)
        mid.add(left, weight=3)
        mid.add(right, weight=2)

        self.canvas = tk.Canvas(left, bg="#2b2b2b", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        ttk.Label(right, text="OCR / Page Text").pack(anchor=tk.W)
        self.ocr_output = ScrolledText(right, wrap=tk.WORD, height=25)
        self.ocr_output.pack(fill=tk.BOTH, expand=True, pady=(4, 8))

        insert_row = ttk.Frame(right)
        insert_row.pack(fill=tk.X, pady=2)
        ttk.Label(insert_row, text="Insert text:").pack(side=tk.LEFT)
        self.insert_text_entry = ttk.Entry(insert_row)
        self.insert_text_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        ttk.Button(insert_row, text="Enable Insert Mode", command=self.enable_insert_mode).pack(side=tk.LEFT)

        self.status = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

    def set_status(self, text: str) -> None:
        self.status.config(text=text)

    def open_pdf(self) -> None:
        path = filedialog.askopenfilename(
            title="Open PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            self.doc = fitz.open(path)
            self.pdf_path = Path(path)
            self.page_index = 0
            self.insert_mode = False
            self.render_page()
            self.set_status(f"Opened: {self.pdf_path}")
        except Exception as exc:
            messagebox.showerror("Open failed", f"Could not open PDF:\n{exc}")

    def render_page(self) -> None:
        if not self.doc:
            return
        page = self.doc[self.page_index]
        matrix = fitz.Matrix(self.zoom, self.zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        self.current_pil_image = img
        self.tk_img = ImageTk.PhotoImage(img)

        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.tk_img, anchor=tk.NW)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

        rect = page.rect
        self.page_scale_x = pix.width / rect.width if rect.width else 1.0
        self.page_scale_y = pix.height / rect.height if rect.height else 1.0
        self.page_label.config(text=f"Page {self.page_index + 1} / {len(self.doc)}")

    def prev_page(self) -> None:
        if not self.doc or self.page_index <= 0:
            return
        self.page_index -= 1
        self.render_page()

    def next_page(self) -> None:
        if not self.doc or self.page_index >= len(self.doc) - 1:
            return
        self.page_index += 1
        self.render_page()

    def ocr_current_page(self) -> None:
        if not self.current_pil_image:
            return
        try:
            text = pytesseract.image_to_string(self.current_pil_image)
            self.ocr_output.delete("1.0", tk.END)
            self.ocr_output.insert(tk.END, text)
            self.set_status("OCR complete for current page.")
        except Exception as exc:
            messagebox.showerror("OCR failed", f"OCR failed:\n{exc}")

    def ocr_all_to_txt(self) -> None:
        if not self.doc:
            return
        save_path = filedialog.asksaveasfilename(
            title="Save OCR text",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not save_path:
            return
        try:
            output_lines: list[str] = []
            for idx in range(len(self.doc)):
                page = self.doc[idx]
                pix = page.get_pixmap(matrix=fitz.Matrix(self.zoom, self.zoom), alpha=False)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                page_text = pytesseract.image_to_string(img)
                output_lines.append(f"--- Page {idx + 1} ---\n{page_text}\n")
            Path(save_path).write_text("\n".join(output_lines), encoding="utf-8")
            self.set_status(f"OCR text saved to: {save_path}")
        except Exception as exc:
            messagebox.showerror("OCR export failed", f"Could not export OCR text:\n{exc}")

    def enable_insert_mode(self) -> None:
        text = self.insert_text_entry.get().strip()
        if not text:
            messagebox.showinfo("Insert text", "Enter text first.")
            return
        self.insert_mode = True
        self.set_status("Insert mode enabled: click on the page to place text.")

    def on_canvas_click(self, event: tk.Event) -> None:
        if not self.doc or not self.insert_mode:
            return
        text = self.insert_text_entry.get().strip()
        if not text:
            self.insert_mode = False
            return

        x_canvas = self.canvas.canvasx(event.x)
        y_canvas = self.canvas.canvasy(event.y)
        x_pdf = x_canvas / self.page_scale_x if self.page_scale_x else x_canvas
        y_pdf = y_canvas / self.page_scale_y if self.page_scale_y else y_canvas

        try:
            page = self.doc[self.page_index]
            page.insert_text((x_pdf, y_pdf), text, fontsize=12, color=(0, 0, 0))
            self.insert_mode = False
            self.set_status("Text inserted. Use Save As to write changes.")
            self.render_page()
        except Exception as exc:
            messagebox.showerror("Insert failed", f"Could not insert text:\n{exc}")

    def save_pdf(self) -> None:
        if not self.doc:
            return
        default_name = "edited.pdf"
        if self.pdf_path:
            default_name = f"{self.pdf_path.stem}_edited.pdf"

        save_path = filedialog.asksaveasfilename(
            title="Save edited PDF",
            initialfile=default_name,
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if not save_path:
            return
        try:
            self.doc.save(save_path)
            self.set_status(f"Saved: {save_path}")
        except Exception as exc:
            messagebox.showerror("Save failed", f"Could not save PDF:\n{exc}")


def main() -> None:
    root = tk.Tk()
    app = PDFEditorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
