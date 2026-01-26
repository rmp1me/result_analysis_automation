import pdfplumber
import re
import pandas as pd
import numpy as np
from analysis_module import process_results


def result_analysis(pdf_path: str, subject_map: dict, semester, progress_callback=None):
    students = []

    # Roman mapping (defined ONCE)
    roman_map = {
        1: "I", 2: "II", 3: "III", 4: "IV",
        5: "V", 6: "VI", 7: "VII", 8: "VIII"
    }

    semester_found = False

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)

        for page_index, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if not text:
                continue

            # -------- Student identification --------
            seat_match = re.search(r"SEAT NO\.:\s*([A-Z0-9]+)", text)
            name_match = re.search(r"NAME:\s*([A-Z\s]+?)\sMother", text)

            if not (seat_match and name_match):
                continue

            # -------- Semester extraction (CORRECT) --------
            sem_match = re.search(r"SEMESTER\s*:\s*([1-8])", text, re.IGNORECASE)
            if not sem_match:
                continue

            sem_digit = int(sem_match.group(1))       # e.g. 3
            pdf_sem = f"Sem {roman_map[sem_digit]}"  # Sem III

            if pdf_sem != semester:
                continue   # skip wrong semester pages

            semester_found = True
            student_dict = {
                "SEAT NUMBER": seat_match.group(1),
                "STUDENT NAME": name_match.group(1).strip()
            }

            sem_text = text[sem_match.end():]

            # -------- Subject marks extraction --------
            for line in sem_text.split("\n"):
                line = line.strip()
                if not line or "SGPA" in line or "Result" in line:
                    continue

                subj_match = re.match(r"([A-Z0-9\-]+(?:_[A-Z]+)?)", line)
                if not subj_match:
                    continue

                subject_code = subj_match.group(1)
                if subject_code not in subject_map:
                    continue

                tokens = line[len(subject_code):].split()
                marks = []

                # for i, token in enumerate(tokens):
                #     if i == 12:
                #         break
                #     if i > 0 and tokens[i - 1] in {"P", "*"}:
                #         if token.isdigit():
                #             marks.append(int(token))
                #         elif token == "AAA":
                #             marks.append("AAA")
                #         else:
                #             token=token.replace("$", "")
                #             if token.isdigit():
                #                 marks.append(int(token))
                for i, token in enumerate(tokens[:12]):
                    if i == 0 or tokens[i - 1] not in {"P", "*"}:
                        continue

                    if token == "AAA":
                        marks.append("AAA")
                        continue

                    clean_token = token.replace("$", "")
                    if clean_token.isdigit():
                        marks.append(int(clean_token))
                            
                if marks:
                    if len(marks) == 1:
                        marks.append(np.nan)
                    student_dict[subject_code] = marks

            # -------- SGPA & credit summary --------
            sgpa_matches = re.findall(
                r"(First|Second|Third|Fourth)\s+Semester\s+SGPA\s*:\s*([\d.]+|-----)\s*"
                r"Credits Earned/Total\s*:\s*(\d+)\s*/\s*(\d+)\s*"
                r"Total Credit Points\s*:\s*(\d+)",
                text,
                re.IGNORECASE
            )

            for sem, sgpa, earned, total, points in sgpa_matches:
                key = sem.lower()
                student_dict[f"{key}_sgpa"] = None if sgpa == "-----" else float(sgpa)
                student_dict[f"{key}_credits_earned"] = int(earned)
                student_dict[f"{key}_credits_total"] = int(total)
                student_dict[f"{key}_total_credit_points"] = int(points)

            students.append(student_dict)

            if progress_callback:
                progress_callback(page_index, total_pages)

    # -------- FINAL VALIDATION --------
    if not semester_found:
        raise ValueError("Selected semester does not match the uploaded PDF")

    df = pd.DataFrame(students)
    if df.empty:
        return df, 0

    df = process_results(df, subject_map, semester)
    return df, len(df)
