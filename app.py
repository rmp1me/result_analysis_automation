import json
import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinter import ttk, PhotoImage
import hashlib
from PIL import Image, ImageTk
from extractor import result_analysis


# ================= PASSWORD PROTECTION =================
def ask_password():
    auth = tk.Tk()
    auth.withdraw()

    password = simpledialog.askstring(
        "Authentication Required",
        "Enter password:",
        show="*"
    )

    correct_hash = hashlib.sha256("admin123".encode()).hexdigest()

    if not password:
        messagebox.showerror("Access Denied", "Password required")
        sys.exit(0)

    if hashlib.sha256(password.encode()).hexdigest() != correct_hash:
        messagebox.showerror("Access Denied", "Incorrect password")
        sys.exit(0)

    auth.destroy()


# ================= APP STATE =================
app_state = {}

CLASS_SEM_MAP = {
    "FE": ["Sem I", "Sem II"],
    "SE": ["Sem III", "Sem IV"],
    "TE": ["Sem V", "Sem VI"],
    "BE": ["Sem VII", "Sem VIII"]
}


# ================= RESOURCE PATH =================
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# ================= LOAD SUBJECT MAP =================
def load_subject_map(class_name, semester):
    with open(resource_path("subject.json"), "r", encoding="utf-8") as f:
        data = json.load(f)

    try:
        return data[class_name.upper()][semester]
    except KeyError:
        raise ValueError(f"No subjects found for {class_name} - {semester}")


# ================= PROGRESS CALLBACK =================
def update_progress(current, total):
    percent = int((current / total) * 100)
    root.after(0, lambda: progress.config(value=percent))


# ================= CLASS CHANGE =================
def on_class_change(event):
    sem_cb["values"] = CLASS_SEM_MAP.get(class_var.get(), [])
    semester_var.set("Select Semester")


# ================= FILE SELECT =================
def select_pdf():
    if class_var.get() == "Select Class" or semester_var.get() == "Select Semester":
        messagebox.showwarning("Input Required", "Please select Class and Semester")
        return

    app_state["class"] = class_var.get()
    app_state["semester"] = semester_var.get()

    pdf_path = filedialog.askopenfilename(
        title="Select SPPU Result PDF",
        filetypes=[("PDF Files", "*.pdf")]
    )

    if not pdf_path:
        return

    upload_btn.config(state="disabled")
    progress["value"] = 0

    try:
        subject_map = load_subject_map(app_state["class"], app_state["semester"])
        threading.Thread(
            target=run_analysis,
            args=(pdf_path, subject_map),
            daemon=True
        ).start()

    except Exception as e:
        messagebox.showerror("Error", str(e))
        upload_btn.config(state="normal")


# ================= WORKER =================
def run_analysis(pdf_path, subject_map):
    try:
        _, total = result_analysis(
            pdf_path,
            subject_map,
            app_state["semester"],
            progress_callback=update_progress
        )
        root.after(0, lambda: on_success(total))
    except Exception as e:
        err = str(e)
        root.after(0, lambda: on_error(err))

# ================= SUCCESS =================
def on_success(total):
    progress["value"] = 100
    messagebox.showinfo(
        "Processing Completed",
        f"Class: {app_state['class']}\n"
        f"Semester: {app_state['semester']}\n"
        f"Total Records: {total}"
    )
    upload_btn.config(state="normal")
    root.destroy()


# ================= ERROR =================
def on_error(msg):
    messagebox.showerror("Error", msg)
    upload_btn.config(state="normal")


# ================= GUI =================
ask_password()

root = tk.Tk()
root.title("Late G.N. Sapkal College of Engineering, Nashik")

icon_img = PhotoImage(file=resource_path("logo.png"))
root.iconphoto(True, icon_img)

WINDOW_W = 700
WINDOW_H = 340

# ---- 60–40 RATIO ----
IMAGE_RATIO = 0.60
FRAME_RATIO = 0.40

LEFT_BAR_WIDTH = int(WINDOW_W * IMAGE_RATIO)
RIGHT_FRAME_WIDTH = int(WINDOW_W * FRAME_RATIO)

x = (root.winfo_screenwidth() - WINDOW_W) // 2
y = (root.winfo_screenheight() - WINDOW_H) // 2

root.geometry(f"{WINDOW_W}x{WINDOW_H}+{x}+{y}")
root.resizable(False, False)

container = ttk.Frame(root, padding=15)
container.pack(fill="both", expand=True)

# ================= LEFT IMAGE PANEL (60%) =================
left_frame = ttk.Frame(container, width=LEFT_BAR_WIDTH)
left_frame.pack(side="left", fill="y", padx=(0, 18))
left_frame.pack_propagate(False)

try:
    img = Image.open(resource_path("side.png"))
    img = img.resize((LEFT_BAR_WIDTH, WINDOW_H - 20), Image.LANCZOS)
    side_img = ImageTk.PhotoImage(img)

    img_lbl = ttk.Label(left_frame, image=side_img)
    img_lbl.image = side_img
    img_lbl.pack(fill="both", expand=True)
except Exception as e:
    print("Image error:", e)

# ================= RIGHT FRAME (40% – SMALL) =================
right_frame = ttk.Frame(
    container,
    width=RIGHT_FRAME_WIDTH,
    padding=14,
    relief="ridge"
)
right_frame.pack(side="left", fill="y")
right_frame.pack_propagate(False)

ttk.Label(
    right_frame,
    text="SPPU Result Analyzer",
    font=("Segoe UI", 14, "bold")
).pack(pady=(0, 6))

ttk.Label(
    right_frame,
    text="Upload an SPPU result PDF to analyze and extract student records.",
    foreground="#555",
    wraplength=240,
    justify="center"
).pack(pady=(0, 15))

class_var = tk.StringVar(value="Select Class")
semester_var = tk.StringVar(value="Select Semester")

form = ttk.Frame(right_frame)
form.pack(pady=(0, 12))

ttk.Label(form, text="Class:").grid(row=0, column=0, sticky="w", pady=4)
class_cb = ttk.Combobox(
    form, textvariable=class_var,
    values=["FE", "SE", "TE", "BE"],
    state="readonly", width=14
)
class_cb.grid(row=0, column=1, padx=(6, 0))
class_cb.bind("<<ComboboxSelected>>", on_class_change)

ttk.Label(form, text="Semester:").grid(row=1, column=0, sticky="w", pady=4)
sem_cb = ttk.Combobox(
    form, textvariable=semester_var,
    state="readonly", width=14
)
sem_cb.grid(row=1, column=1, padx=(6, 0))

upload_btn = tk.Button(
    right_frame,
    text="Upload Result PDF",
    font=("Segoe UI", 11, "bold"),
    width=18,
    pady=6,
    command=select_pdf
)
upload_btn.pack(pady=(12, 8))

ttk.Separator(right_frame).pack(fill="x", padx=30, pady=(3, 6))

progress = ttk.Progressbar(
    right_frame,
    orient="horizontal",
    length=260,
    mode="determinate"
)
progress.pack(pady=(12, 0))

root.mainloop()
