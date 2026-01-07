import pdfplumber
import re
import pprint
import pandas as pd

all_students = []

pdf_path = r"C:\Users\Riyansh\Desktop\automation_work\FE_2024_TESTING_NEW.pdf"

with pdfplumber.open(pdf_path) as pdf:
    for page_no, page in enumerate(pdf.pages, start=1):
        text = page.extract_text()
        if not text:
            continue

        seat_match = re.search(r"SEAT NO\.:\s*([A-Z0-9]+)", text)
        name_match = re.search(r"NAME:([A-Z\s]+?)\sMother", text)

        if not (seat_match and name_match):
            continue

        seat_no = seat_match.group(1)
        stud_name = name_match.group(1).strip()

        # ---------- Semester 1 block ----------
        try:
            sem_text = text.split("Semester : 1")[1]
        except IndexError:
            continue

        subjects_list = []      
        
               
        for line in sem_text.split("\n"):
            print(line)
            if "SGPA" in line or "Result" in line:
                continue

            subj_match = re.match(r"([A-Z0-9\-]+(?:_TW)?)", line)
            if not subj_match:
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
                        marks.append(token)   # AAA, FFF, etc.

            if marks:
                subjects_list.append([subject] + marks)

        # ---------- SGPA extraction ----------
        sgpa_match = re.search(
            r"First Semester SGPA\s*:\s*(.*?)\s*Credits Earned/Total\s*:\s*(\d+)/(\d+)\s*Total Credit Points\s*:\s*(\d+)",
            text
        )

        first_sem_result = {}
        if sgpa_match:
            first_sem_result = {
                "sgpa": sgpa_match.group(1).strip(),
                "credits_earned": int(sgpa_match.group(2)),
                "credits_total": int(sgpa_match.group(3)),
                "total_credit_points": int(sgpa_match.group(4))
            }

        student_data = {
            "seatNo": seat_no,
            "stud_name": stud_name,
            "subjects": subjects_list,
            "first_semester_summary": first_sem_result
        }

        all_students.append(student_data)
        print(student_data)

pprint.pprint(all_students, width=120)

rows = []

for student in all_students:
    row = {
        "Seat No": student["seatNo"],
        "Student Name": student["stud_name"],
    }

    # Add subject marks
    for subject_data in student["subjects"]:
        subject = subject_data[0]
        marks = subject_data[1:]
        row[subject] = ",".join(map(str, marks))  # keep sequence

    # Add SGPA summary
    summary = student.get("first_semester_summary", {})
    row["SGPA"] = summary.get("sgpa", "")
    row["Credits Earned"] = summary.get("credits_earned", "")
    row["Credits Total"] = summary.get("credits_total", "")
    row["Total Credit Points"] = summary.get("total_credit_points", "")

    rows.append(row)

# Create DataFrame
df = pd.DataFrame(rows)

# Export to Excel
output_file = r"C:\Users\Riyansh\Desktop\FE_2024_Sem1_Result_one.xlsx"
df.to_excel(output_file, index=False)

print("Excel file created successfully:", output_file)

