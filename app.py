import json
import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk, PhotoImage
from extractor import result_analysis

# ---------------- APP STATE ----------------
app_state = {}

# NEW: CLASS → SEMESTER MAPPING 
CLASS_SEM_MAP = {
    "FE": ["Sem I", "Sem II"],
    "SE": ["Sem III", "Sem IV"],
    "TE": ["Sem V", "Sem VI"],
    "BE": ["Sem VII", "Sem VIII"]
}

# ---------------- RESOURCE PATH (EXE SAFE) ----------------
def resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# ---------------- LOAD SUBJECT MAP (CLASS + SEMESTER) ----------------
def load_subject_map(class_name: str, semester: str) -> dict:
    with open(resource_path("subject.json"), "r", encoding="utf-8") as f:
        data = json.load(f)

    class_name = class_name.upper()

    try:
        return data[class_name][semester]
    except KeyError:
        raise ValueError(f"No subjects found for {class_name} - {semester}")


# ---------------- PROGRESS CALLBACK ----------------
def update_progress(current, total):
    percent = int((current / total) * 100)
    root.after(0, lambda: progress.config(value=percent))


# NEW: CLASS CHANGE HANDLER 
def on_class_change(event):
    selected_class = class_var.get()
    sem_cb["values"] = CLASS_SEM_MAP.get(selected_class, [])
    semester_var.set("Select Semester")


# ---------------- BUTTON HANDLER ----------------
def select_pdf():
    selected_class = class_var.get()
    selected_sem = semester_var.get()

    if selected_class == "Select Class" or selected_sem == "Select Semester":
        messagebox.showwarning(
            "Input Required",
            "Please select Class and Semester"
        )
        return

    app_state["class"] = selected_class
    app_state["semester"] = selected_sem

    pdf_path = filedialog.askopenfilename(
        title="Select SPPU Result PDF",
        filetypes=[("PDF Files", "*.pdf")]
    )

    if not pdf_path:
        return

    upload_btn.config(state="disabled")
    progress["value"] = 0

    try:
        subject_map = load_subject_map(
            app_state["class"],
            app_state["semester"]
        )

        threading.Thread(
            target=run_analysis,
            args=(pdf_path, subject_map, app_state["class"],app_state["semester"]),
            daemon=True
        ).start()

    except Exception as e:
        messagebox.showerror("Error", str(e))
        upload_btn.config(state="normal")


# ---------------- BACKGROUND WORKER ----------------
def run_analysis(pdf_path, subject_map, class_name,semester):
    try:
        _, total_records = result_analysis(
            pdf_path,
            subject_map,
            semester,
            progress_callback=update_progress
        )
        root.after(0, lambda: on_success(class_name, total_records))
    except Exception as e:
        root.after(0, lambda: on_error(str(e)))


# ---------------- SUCCESS HANDLER ----------------
def on_success(class_name, total_records):
    progress["value"] = 100

    messagebox.showinfo(
        "Processing Completed",
        f"Result processed successfully.\n\n"
        f"Class: {class_name}\n"
        f"Semester: {app_state['semester']}\n"
        f"Total Records: {total_records}"
    )

    upload_btn.config(state="normal")
    root.destroy()


# ---------------- ERROR HANDLER ----------------
def on_error(msg):
    messagebox.showerror("Error", msg)
    upload_btn.config(state="normal")


# ================= GUI =================
root = tk.Tk()
root.title("Late G.N. Sapkal College of Engineering,Nashik")

icon_img = PhotoImage(file=resource_path("logo.png"))
root.iconphoto(True, icon_img)

WINDOW_W = 550
WINDOW_H = 315

screen_w = root.winfo_screenwidth()
screen_h = root.winfo_screenheight()
x = (screen_w - WINDOW_W) // 2
y = (screen_h - WINDOW_H) // 2

root.geometry(f"{WINDOW_W}x{WINDOW_H}+{x}+{y}")
root.resizable(False, False)

container = ttk.Frame(root, padding=15)
container.pack(fill="both", expand=True)

LEFT_BAR_WIDTH = 200
left_frame = ttk.Frame(container, width=LEFT_BAR_WIDTH)
left_frame.pack(side="left", fill="y", padx=(0, 15))
left_frame.pack_propagate(False)

try:
    side_img = PhotoImage(file=resource_path("side.png"))
    ttk.Label(left_frame, image=side_img).place(relx=0.5, rely=0.5, anchor="center")     
    
except:
    pass

right_frame = ttk.Frame(container)
right_frame.pack(side="left", fill="both", expand=True)

ttk.Label(
    right_frame,
    text="SPPU Result Analyzer",
    font=("Segoe UI", 14, "bold")
).pack(pady=(0, 6))

ttk.Label(
    right_frame,
    text="Upload an SPPU result PDF to analyze and extract student records.",
    foreground="#555",
    wraplength=230,
    justify="center"
).pack(pady=(0, 15))

# ================= CLASS & SEMESTER =================
class_var = tk.StringVar(value="Select Class")
semester_var = tk.StringVar(value="Select Semester")

form_frame = ttk.Frame(right_frame)
# form_frame.pack(pady=(0, 10))
form_frame.pack(pady=(0, 10), anchor="center")

ttk.Label(form_frame, text="Class:").grid(row=0, column=0, sticky="w", pady=4)

#  UPDATED: bind class change 
class_cb = ttk.Combobox(
    form_frame,
    textvariable=class_var,
    values=["FE", "SE", "TE", "BE"],
    state="readonly",
    width=15
)
class_cb.grid(row=0, column=1, pady=4)
class_cb.bind("<<ComboboxSelected>>", on_class_change)

ttk.Label(form_frame, text="Semester:").grid(row=1, column=0, sticky="w", pady=4)

# UPDATED: semester values removed 
sem_cb = ttk.Combobox(
    form_frame,
    textvariable=semester_var,
    state="readonly",
    width=15
)
sem_cb.grid(row=1, column=1, pady=4)

upload_btn = tk.Button(
    right_frame,
    text="Upload Result PDF",
    font=("Segoe UI", 11, "bold"),
    width=20,
    pady=6,
    command=select_pdf
)
upload_btn.pack(pady=(10, 10))

progress = ttk.Progressbar(
    right_frame,
    orient="horizontal",
    length=300,
    mode="determinate"
)
# progress.pack(pady=(0, 5))
progress.pack(pady=(5, 0))

root.mainloop()
