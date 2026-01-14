import json
import os
import sys
import threading   
from tkinter import Tk, Button, filedialog, messagebox
from tkinter import ttk, PhotoImage
from extractor import result_analysis


# ---------------- RESOURCE PATH (EXE SAFE) ----------------
def resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# ---------------- LOAD SUBJECT MAP ----------------
def load_subject_map(class_name: str) -> dict:
    try:
        with open(resource_path("subject.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError("subject.json not found")
    except json.JSONDecodeError:
        raise ValueError("subject.json is not valid JSON")

    class_name = class_name.upper()

    if class_name in data:
        return data[class_name]

    raise ValueError(f"Class {class_name} not found in subject.json")


# ---------------- PROGRESS CALLBACK (GUI SAFE) ----------------
def update_progress(current, total):
    percent = int((current / total) * 100)

    #  Always update GUI on main thread
    root.after(0, lambda: progress.config(value=percent))


# ---------------- EXTRACT CLASS ----------------
def extract_class_from_filename(pdf_path: str) -> str:
    file_name = os.path.basename(pdf_path)
    name = file_name.split(".")[0]
    class_name = name.split("_")[0]
    return class_name.upper()


# ---------------- BUTTON HANDLER ----------------
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
        class_name = extract_class_from_filename(pdf_path)

        if class_name not in ("FE", "SE", "TE", "BE"):
            raise ValueError("Invalid file name format. Class not found.")

        subject_map = load_subject_map(class_name)

        # =================================================
        # START BACKGROUND THREAD (NON-BLOCKING)
        # =================================================
        threading.Thread(
            target=run_analysis,
            args=(pdf_path, subject_map, class_name),
            daemon=True
        ).start()

    except Exception as e:
        messagebox.showerror("Error", str(e))
        upload_btn.config(state="normal")


# ---------------- BACKGROUND WORKER (THREAD) ----------------
def run_analysis(pdf_path, subject_map, class_name):
    try:
        df, total_records = result_analysis(
            pdf_path,
            subject_map,
            progress_callback=update_progress
        )

        #  Send success back to GUI thread
        root.after(0, lambda: on_success(class_name, total_records))

    except Exception as e:
        root.after(0, lambda: on_error(str(e)))


# ---------------- GUI SUCCESS HANDLER ----------------
def on_success(class_name, total_records):
    progress["value"] = 100

    messagebox.showinfo(
        "Success",
        f"Result processed successfully!\n\n"
        f"Class: {class_name}\n"
        f"Total Records: {total_records}"
    )

    root.after(500, root.destroy)


# ---------------- GUI ERROR HANDLER ----------------
def on_error(msg):
    messagebox.showerror("Error", msg)
    upload_btn.config(state="normal")


# ================= GUI =================
root = Tk()
root.title("SPPU Result Analyzer")

# -------- ICON (EXE SAFE) --------
icon_path = resource_path("logo.png")
icon = PhotoImage(file=icon_path)
root.iconphoto(True, icon)
# --------------------------------

# Center window
window_width = 420
window_height = 230

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

x = (screen_width - window_width) // 2
y = (screen_height - window_height) // 2

root.geometry(f"{window_width}x{window_height}+{x}+{y}")

# Upload button
upload_btn = Button(
    root,
    text="Upload Result PDF",
    font=("Arial", 14),
    width=20,
    command=select_pdf
)
upload_btn.pack(pady=20)

# Progress bar
progress = ttk.Progressbar(
    root,
    orient="horizontal",
    length=320,
    mode="determinate"
)
progress.pack(pady=10)

root.mainloop()
