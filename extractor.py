import pdfplumber
import re
import pandas as pd
import json
import os
import sys
import numpy as np

from analysis_module import process_results


def result_analysis(pdf_path: str, subject_map: dict,progress_callback=None) -> None:
    """
    Extracts student-wise subject marks and semester summaries from an SPPU
    result PDF and exports a processed Excel report.

    Only subjects present in subject_map (loaded from subject.json)
    are considered for mark extraction.

    Args:
        pdf_path (str): Absolute path to the result PDF file.
        subject_map (dict): Dictionary of valid subject codes to subject names.
                            Example: {"210241": "Discrete Mathematics", ...}

    Returns:
        None
    """
    students = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
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

                # Process ONLY subjects defined in subject.json
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

            # -------- SGPA & credit summary extraction --------
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
                progress_callback(page.page_number, len(pdf.pages))

   
    # -------- DataFrame creation & post-processing --------
    df = pd.DataFrame(students)

    if df.empty:
        print("No student data extracted.")
        return

    df = process_results(df, subject_map)
    df.to_excel("Processed_Results_Final_output_verified.xlsx", index=False)
    total_records = len(df)
    return df,total_records


def resource_path(relative_path: str) -> str:
    """
    Resolves the absolute path of a resource file.
    Supports PyInstaller packaged execution.
   
    Args:
        relative_path (str): Relative file path.

    Returns:
        str: Absolute file path.
    """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def main() -> None:
    """
    Entry point of the result analysis script.
    Loads subject.json, validates configuration, and
    triggers PDF result processing.
    """
    try:
        with open(resource_path("subject.json"), "r", encoding="utf-8") as f:
            data = json.load(f)

        subject_map = data.get("SE") or data.get("TE") or data.get("BE")
        if not subject_map:
            raise KeyError("SE / TE / BE not found in subject.json")

    except Exception as e:
        print("ERROR: Unable to load subject.json")
        print(e)
        return

    pdf_path = r"C:\Users\Riyansh\Desktop\automation_work\SE_2019_Computer Regular_9.pdf"
    result_analysis(pdf_path, subject_map)


# if __name__ == "__main__":
#     main()
