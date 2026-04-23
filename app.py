from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
import fitz  # PyMuPDF
import pytesseract
from PIL import Image, ImageTk


class PDFEditorApp:
    def __init__(self, root: ctk.CTk) -> None:
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
        self._undo_stack: list[dict] = []

        self._build_ui()

    def _build_ui(self) -> None:
        top = ctk.CTkFrame(self.root)
        top.pack(fill="x", padx=8, pady=8)

        ctk.CTkButton(top, text="Open PDF", command=self.open_pdf).pack(side="left", padx=4)
        ctk.CTkButton(top, text="Save As", command=self.save_pdf).pack(side="left", padx=4)
        ctk.CTkButton(top, text="Undo", command=self.undo_last).pack(side="left", padx=4)
        ctk.CTkButton(top, text="Previous", command=self.prev_page).pack(side="left", padx=4)
        ctk.CTkButton(top, text="Next", command=self.next_page).pack(side="left", padx=4)
        ctk.CTkButton(top, text="OCR Page", command=self.ocr_current_page).pack(side="left", padx=4)
        ctk.CTkButton(top, text="OCR All -> TXT", command=self.ocr_all_to_txt).pack(side="left", padx=4)

        self.page_label = ctk.CTkLabel(top, text="No file loaded")
        self.page_label.pack(side="right", padx=4)

        mid = ctk.CTkFrame(self.root)
        mid.pack(fill="both", expand=True)
        mid.columnconfigure(0, weight=3)
        mid.columnconfigure(1, weight=2)
        mid.rowconfigure(0, weight=1)

        left = ctk.CTkFrame(mid)
        left.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        right = ctk.CTkFrame(mid)
        right.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)

        self.canvas = tk.Canvas(left, bg="#2b2b2b", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        ctk.CTkLabel(right, text="OCR / Page Text").pack(anchor="w")
        self.ocr_output = ctk.CTkTextbox(right, wrap="word", height=400)
        self.ocr_output.pack(fill="both", expand=True, pady=(4, 8))

        insert_row = ctk.CTkFrame(right)
        insert_row.pack(fill="x", pady=2)
        ctk.CTkLabel(insert_row, text="Insert text:").pack(side="left")
        self.insert_text_entry = ctk.CTkEntry(insert_row)
        self.insert_text_entry.pack(side="left", fill="x", expand=True, padx=4)
        ctk.CTkButton(insert_row, text="Enable Insert Mode", command=self.enable_insert_mode).pack(side="left")

        status_frame = ctk.CTkFrame(self.root, height=24)
        status_frame.pack(fill="x", side="bottom")
        self.status = ctk.CTkLabel(status_frame, text="Ready", anchor="w")
        self.status.pack(fill="x", padx=6)

        self.root.bind("<Control-z>", lambda e: self.undo_last())

    def set_status(self, text: str) -> None:
        self.status.configure(text=text)

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
            self._undo_stack.clear()
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
        self.page_label.configure(text=f"Page {self.page_index + 1} / {len(self.doc)}")

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
            self.ocr_output.delete("1.0", "end")
            self.ocr_output.insert("end", text)
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
            snapshot = {
                "page_index": self.page_index,
                "contents": page.read_contents(),
            }
            self._undo_stack.append(snapshot)
            if len(self._undo_stack) > 100:
                self._undo_stack.pop(0)
            text_width = fitz.get_text_length(text, fontname="helv", fontsize=12)
            x_centered = x_pdf - text_width / 2
            y_centered = y_pdf + 6  # offset up by half font size
            page.insert_text((x_centered, y_centered), text, fontsize=12, color=(0, 0, 0))
            self.insert_mode = False
            self.set_status("Text inserted. Use Save As to write changes.")
            self.render_page()
        except Exception as exc:
            messagebox.showerror("Insert failed", f"Could not insert text:\n{exc}")

    def undo_last(self) -> None:
        if not self._undo_stack:
            self.set_status("Nothing to undo.")
            return
        snapshot = self._undo_stack.pop()
        try:
            page = self.doc[snapshot["page_index"]]
            page.clean_contents()
            contents = page.get_contents()
            if not contents:
                self.set_status("Nothing to undo.")
                return
            xref = contents[0]
            self.doc.update_stream(xref, snapshot["contents"])
            self.render_page()
            self.set_status("Undo successful.")
        except Exception as exc:
            messagebox.showerror("Undo failed", f"Could not undo:\n{exc}")

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
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    app = PDFEditorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
