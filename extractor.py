import pdfplumber
import re
import pandas as pd
import numpy as np

from analysis_module import process_results


def result_analysis(pdf_path: str, subject_map: dict, progress_callback=None):
    """
    Extracts student-wise subject marks and semester summaries from an SPPU
    result PDF and exports a processed Excel report.

    Args:
        pdf_path (str): Absolute path to the result PDF file.
        subject_map (dict): Dictionary of valid subject codes to subject names.
        progress_callback (callable, optional): Function to update progress.
            Called as progress_callback(current, total)

    Returns:
        tuple: (DataFrame, total_records)
    """
    students = []

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

            student_dict = {
                "SEAT NUMBER": seat_match.group(1),
                "STUDENT NAME": name_match.group(1).strip()
            }

            # -------- Semester block extraction --------
            sem_match = re.search(r"SEMESTER\s*:\s*[1-8]", text, re.IGNORECASE)
            if not sem_match:
                continue

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

                rest_of_line = line[len(subject_code):].strip()
                tokens = rest_of_line.split()

                marks = []
                for i, token in enumerate(tokens):
                    if i == 12:
                        break

                    if i > 0 and tokens[i - 1] in {"P", "*"}:
                        if token.isdigit():
                            marks.append(int(token))
                        elif token == "AAA":
                            marks.append("AAA")
                        else:
                            clean = re.sub(r"\D", "", token)
                            if clean:
                                marks.append(int(clean))

                if marks:
                    if len(marks) == 1:
                        marks = [marks[0], np.nan]
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

            # ✅ SAFE PROGRESS UPDATE
            if progress_callback:
                progress_callback(page_index, total_pages)

    # -------- DataFrame creation & post-processing --------
    df = pd.DataFrame(students)

    if df.empty:
        return df, 0

    df = process_results(df, subject_map)
    df.to_excel("Processed_Results_Final_output_verified1111.xlsx", index=False)

    return df, len(df)
    