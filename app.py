import json
from tkinter import Tk, Button, filedialog, messagebox
from tkinter import ttk

from result_analysis_1 import result_analysis

def load_subject_map():
    with open("subject.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    for cls in ("FE", "SE", "TE", "BE"):
        if cls in data:
            return data[cls]

    raise ValueError("No class found")

def update_progress(current, total):
    percent = int((current / total) * 100)
    progress["value"] = percent
    root.update_idletasks()   # keeps UI responsive

def select_pdf():
    pdf_path = filedialog.askopenfilename(
        title="Select SPPU Result PDF",
        filetypes=[("PDF Files", "*.pdf")]
    )

    if not pdf_path:
        return

    upload_btn.config(state="disabled")
    progress["value"] = 0

    try:
        subject_map = load_subject_map()

        df, total_records = result_analysis(
            pdf_path,
            subject_map,
            progress_callback=update_progress
        )

        messagebox.showinfo(
            "Success",
            f"Result processed successfully!\n\n"
            f"Total Records: {total_records}"
        )

        root.after(500, root.destroy)

    except Exception as e:
        messagebox.showerror("Error", str(e))
        upload_btn.config(state="normal")

# -------- GUI --------
root = Tk()
root.title("SPPU Result Analyzer")
root.geometry("420x230")

upload_btn = Button(
    root,
    text="Upload Result PDF",
    font=("Arial", 14),
    width=20,
    command=select_pdf
)
upload_btn.pack(pady=20)

progress = ttk.Progressbar(
    root,
    orient="horizontal",
    length=320,
    mode="determinate"
)
progress.pack(pady=10)

root.mainloop()
