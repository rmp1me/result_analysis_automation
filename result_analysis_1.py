import pdfplumber
import re
import pprint
import pandas as pd

students = []

pdf_path = r"C:\Users\Riyansh\Desktop\automation_work\FE_2024_ALL.pdf"

with pdfplumber.open(pdf_path) as pdf:
    for page_no, page in enumerate(pdf.pages, start=1):
        text = page.extract_text()
        if not text:
            continue

        # Extract seat number and student name
        seat_match = re.search(r"SEAT NO\.:\s*([A-Z0-9]+)", text)
        name_match = re.search(r"NAME:([A-Z\s]+?)\sMother", text)

        if not (seat_match and name_match):
            continue

        seat_no = seat_match.group(1)
        student_name = name_match.group(1).strip()

        # Extract semester text
        try:
            sem_text = text.split("Semester : 1")[1]
        except IndexError:
            continue

        student_dict = {
            "SEAT NUMBER": seat_no,
            "STUDENT NAME": student_name
        }

        # Extract subject marks
        for line in sem_text.split("\n"):
            if "SGPA" in line or "Result" in line:
                continue

            subj_match = re.match(r"([A-Z0-9\-]+(?:_[A-Z]+)?)", line)
            # print(subj_match)
            if not (subj_match and subj_match.group(1).startswith(("BSC", "ESC","PCC")) and not subj_match.group(1).endswith("_TW")):
                continue

            subject = subj_match.group(1)
            rest_of_line = line[len(subject):].strip()
            tokens = rest_of_line.split()
            marks = []

            for i, token in enumerate(tokens):
                if i > 0 and tokens[i - 1] in ["P", "*"]:
                    if token.isdigit():
                        marks.append(int(token))
                    else:
                        marks.append(token)

            if marks:
                # If single mark, store as int, else as list
                student_dict[subject] = marks if len(marks) > 1 else marks[0]

        # Extract SGPA summary
        matches = re.findall(
                                r"(First|Second)\s+Semester\s+SGPA\s*:\s*([\d.]+|-----)\s*"
                                r"Credits Earned/Total\s*:\s*(\d+)\s*/\s*(\d+)\s*"
                                r"Total Credit Points\s*:\s*(\d+)",
                                text,
                                re.IGNORECASE
                            )

        # student_dict = {}

        for sem, sgpa, earned, total, points in matches:
            key = sem.lower()  # first / second

            student_dict[f"{key}_sgpa"] = None if sgpa == "-----" else float(sgpa)
            student_dict[f"{key}_credits_earned"] = int(earned)
            student_dict[f"{key}_credits_total"] = int(total)
            student_dict[f"{key}_total_credit_points"] = int(points)


        students.append(student_dict)

# Print JSON-like structure
pprint.pprint(students, width=120)

# ---------------- Create DataFrame ----------------
df = pd.DataFrame(students)
new_order = [
    "SEAT NUMBER",
    "STUDENT NAME",

    # Semester 1 subjects
    "BSC-101-BES",
    "BSC-102-BES-1",
    "ESC-102-ELE-1",
    "ESC-103-MEC-1",
    "ESC-105-COM",
    "BSC-103-BES-2",
    "BSC-151-BES",
    "ESC-101-ETC-2",
    "ESC-104-CVL-2",
    "PCC-151-ITT",

    # Semester 2 subjects
    "BSC-103-BES-1",
    "ESC-101-ETC-1",
    "ESC-104-CVL-1",
    "BSC-102-BES-2",
    "ESC-102-ELE-2",
    "ESC-103-MEC-2",

    # SGPA summary
    "first_sgpa",
    "first_credits_earned",
    "first_credits_total",
    "first_total_credit_points",

    "second_sgpa",
    "second_credits_earned",
    "second_credits_total",
    "second_total_credit_points"
]
df = df[new_order]


# Export to Excel
output_file = r"FE_2024_Sem1_Result_1_out_final.xlsx"
df.to_excel(output_file, index=False)

print("Excel file created successfully:", output_file)
