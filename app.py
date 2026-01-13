import json
import os
from tkinter import Tk, Button, filedialog, messagebox
from tkinter import ttk
from tkinter import PhotoImage
from extractor import result_analysis


def load_subject_map(class_name: str) -> dict:
    try:
        with open("subject.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError("subject.json not found")
    except json.JSONDecodeError:
        raise ValueError("subject.json is not valid JSON")

    class_name = class_name.upper()

    if class_name in data:
        return data[class_name]

    raise ValueError(f"Class {class_name} not found in subject.json")


def update_progress(current, total):
    percent = int((current / total) * 100)
    progress["value"] = percent
    root.update_idletasks()


def extract_class_from_filename(pdf_path: str) -> str:
    file_name = os.path.basename(pdf_path)
    name = file_name.split(".")[0]      # remove .pdf
    class_name = name.split("_")[0]     # SE / TE / BE
    return class_name.upper()


def select_pdf():
    pdf_path = filedialog.askopenfilename(
        title="Select SPPU Result PDF",
        filetypes=[("PDF Files", "*.pdf")]
    )

    if not pdf_path:   # user cancelled
        return

    upload_btn.config(state="disabled")
    progress["value"] = 0

    try:
        class_name = extract_class_from_filename(pdf_path)

        if class_name not in ("FE", "SE", "TE", "BE"):
            raise ValueError("Invalid file name format. Class not found.")

        subject_map = load_subject_map(class_name)
        df, total_records = result_analysis(
            pdf_path,
            subject_map,
            progress_callback=update_progress
        )

        messagebox.showinfo(
            "Success",
            f"Result processed successfully!\n\n"
            f"Class: {class_name}\n"
            f"Total Records: {total_records}"
        )

        root.after(500, root.destroy)

    except Exception as e:
        messagebox.showerror("Error", str(e))
        upload_btn.config(state="normal")


# -------- GUI --------
root = Tk()
root.title("SPPU Result Analyzer")


# ----- SET LOGO HERE -----
root.iconbitmap("logo.ico")
# ----- END LOGO -----


root.update_idletasks()

window_width = 420
window_height = 230

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

x = (screen_width - window_width) // 2
y = (screen_height - window_height) // 2

root.geometry(f"{window_width}x{window_height}+{x}+{y}")


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
