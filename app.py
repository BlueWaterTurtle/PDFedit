from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
import fitz  # PyMuPDF
import pytesseract
from PIL import Image, ImageTk


class PDFEditorApp:
    _HIT_TEST_RADIUS = 72  # max distance in PDF points (~1 inch) to snap to a text block

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
        self.select_mode = False
        self.selected_block: dict | None = None
        self._undo_stack: list[dict] = []

        self._build_ui()

    def _build_ui(self) -> None:
        top = ctk.CTkFrame(self.root)
        top.pack(fill="x", padx=8, pady=8)

        ctk.CTkButton(top, text="Open PDF", command=self.open_pdf).pack(side="left", padx=4)
        ctk.CTkButton(top, text="Save As", command=self.save_pdf).pack(side="left", padx=4)
        ctk.CTkButton(top, text="Undo", command=self.undo_last).pack(side="left", padx=4)
        self.select_mode_btn = ctk.CTkButton(top, text="Select Mode", command=self.toggle_select_mode)
        self.select_mode_btn.pack(side="left", padx=4)
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

        edit_row = ctk.CTkFrame(right)
        edit_row.pack(fill="x", pady=2)
        ctk.CTkButton(edit_row, text="Apply Edit", command=self.apply_edit_to_selected).pack(side="left", padx=4)
        ctk.CTkButton(edit_row, text="Delete Selected", command=self.delete_selected).pack(side="left", padx=4)

        status_frame = ctk.CTkFrame(self.root, height=24)
        status_frame.pack(fill="x", side="bottom")
        self.status = ctk.CTkLabel(status_frame, text="Ready", anchor="w")
        self.status.pack(fill="x", padx=6)

        self.root.bind("<Control-z>", lambda e: self.undo_last())
        self.root.bind("<Delete>", lambda e: self.delete_selected())

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
            self.select_mode = False
            self.selected_block = None
            self.select_mode_btn.configure(fg_color=["#3B8ED0", "#1F6AA5"])
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
        if self.selected_block:
            self._draw_selection_highlight()

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
        if self.select_mode:
            self.select_mode = False
            self.selected_block = None
            self.select_mode_btn.configure(fg_color=["#3B8ED0", "#1F6AA5"])
        self.set_status("Insert mode enabled: click on the page to place text.")

    def on_canvas_click(self, event: tk.Event) -> None:
        if not self.doc:
            return

        x_canvas = self.canvas.canvasx(event.x)
        y_canvas = self.canvas.canvasy(event.y)
        x_pdf = x_canvas / self.page_scale_x if self.page_scale_x else x_canvas
        y_pdf = y_canvas / self.page_scale_y if self.page_scale_y else y_canvas

        if self.select_mode:
            if event.state & 0x0001 and self.selected_block:
                self._move_selected(x_pdf, y_pdf)
            else:
                self._hit_test_text_blocks(x_pdf, y_pdf)
            return

        if not self.insert_mode:
            return
        text = self.insert_text_entry.get().strip()
        if not text:
            self.insert_mode = False
            return

        try:
            page = self.doc[self.page_index]
            self._push_snapshot()
            text_width = fitz.get_text_length(text, fontname="helv", fontsize=12)
            x_centered = x_pdf - text_width / 2
            y_centered = y_pdf + 6  # offset up by half font size
            page.insert_text((x_centered, y_centered), text, fontsize=12, color=(0, 0, 0))
            self.insert_mode = False
            self.set_status("Text inserted. Use Save As to write changes.")
            self.render_page()
        except Exception as exc:
            messagebox.showerror("Insert failed", f"Could not insert text:\n{exc}")

    def toggle_select_mode(self) -> None:
        if not self.doc:
            return
        self.select_mode = not self.select_mode
        if self.select_mode:
            self.insert_mode = False
            self.select_mode_btn.configure(fg_color="#2CC985")
            self.set_status("Select mode enabled: click a text block to select it. Shift+click to move selected.")
        else:
            self.selected_block = None
            self.select_mode_btn.configure(fg_color=["#3B8ED0", "#1F6AA5"])
            self.set_status("Select mode disabled.")
            self.render_page()

    def _push_snapshot(self) -> None:
        page = self.doc[self.page_index]
        snapshot = {
            "page_index": self.page_index,
            "contents": page.read_contents(),
        }
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > 100:
            self._undo_stack.pop(0)

    def _hit_test_text_blocks(self, x_pdf: float, y_pdf: float) -> None:
        page = self.doc[self.page_index]
        blocks = page.get_text("dict")["blocks"]

        best_block = None
        best_dist = float("inf")

        for block in blocks:
            if block.get("type") != 0:  # type 0 = text block
                continue
            x0, y0, x1, y1 = block["bbox"]
            if x0 <= x_pdf <= x1 and y0 <= y_pdf <= y1:
                best_block = block
                best_dist = 0.0
                break
            cx = (x0 + x1) / 2
            cy = (y0 + y1) / 2
            dist = ((x_pdf - cx) ** 2 + (y_pdf - cy) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best_block = block

        if best_block is not None and best_dist < self._HIT_TEST_RADIUS:
            text_content = ""
            for line in best_block.get("lines", []):
                line_text = " ".join(span.get("text", "") for span in line.get("spans", []))
                if text_content:
                    text_content += "\n"
                text_content += line_text

            self.selected_block = {
                "bbox": best_block["bbox"],
                "text": text_content,
            }
            self.insert_text_entry.delete(0, "end")
            self.insert_text_entry.insert(0, text_content)
            self._draw_selection_highlight()
            self.set_status(f"Selected: '{text_content[:60]}'")
        else:
            self.selected_block = None
            self.render_page()
            self.set_status("No text block found at click position.")

    def _draw_selection_highlight(self) -> None:
        if not self.selected_block:
            return
        x0, y0, x1, y1 = self.selected_block["bbox"]
        cx0 = x0 * self.page_scale_x
        cy0 = y0 * self.page_scale_y
        cx1 = x1 * self.page_scale_x
        cy1 = y1 * self.page_scale_y
        self.canvas.create_rectangle(cx0, cy0, cx1, cy1, outline="cyan", width=2, tags="selection")

    def apply_edit_to_selected(self) -> None:
        if not self.doc or not self.selected_block:
            messagebox.showinfo("No selection", "Select a text block first using Select Mode.")
            return
        new_text = self.insert_text_entry.get().strip()
        if not new_text:
            messagebox.showinfo("No text", "Enter replacement text in the text entry field.")
            return

        page = self.doc[self.page_index]
        bbox = self.selected_block["bbox"]
        self._push_snapshot()
        try:
            page.add_redact_annot(fitz.Rect(bbox))
            page.apply_redactions()
            x0, y1 = bbox[0], bbox[3]
            page.insert_text((x0, y1), new_text, fontsize=12, color=(0, 0, 0))
            self.selected_block = None
            self.set_status("Edit applied. Use Save As to write changes.")
            self.render_page()
        except Exception as exc:
            messagebox.showerror("Edit failed", f"Could not apply edit:\n{exc}")

    def delete_selected(self, event: tk.Event | None = None) -> None:
        if not self.doc or not self.selected_block:
            return
        page = self.doc[self.page_index]
        bbox = self.selected_block["bbox"]
        self._push_snapshot()
        try:
            page.add_redact_annot(fitz.Rect(bbox))
            page.apply_redactions()
            self.selected_block = None
            self.set_status("Element deleted. Use Save As to write changes.")
            self.render_page()
        except Exception as exc:
            messagebox.showerror("Delete failed", f"Could not delete element:\n{exc}")

    def _move_selected(self, x_pdf: float, y_pdf: float) -> None:
        if not self.doc or not self.selected_block:
            return
        page = self.doc[self.page_index]
        bbox = self.selected_block["bbox"]
        text = self.selected_block["text"]
        self._push_snapshot()
        try:
            page.add_redact_annot(fitz.Rect(bbox))
            page.apply_redactions()
            text_width = fitz.get_text_length(text, fontname="helv", fontsize=12)
            x_centered = x_pdf - text_width / 2
            y_centered = y_pdf + 6
            page.insert_text((x_centered, y_centered), text, fontsize=12, color=(0, 0, 0))
            self.selected_block = None
            self.set_status("Element moved. Use Save As to write changes.")
            self.render_page()
        except Exception as exc:
            messagebox.showerror("Move failed", f"Could not move element:\n{exc}")

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
