import pdfplumber
import re
import pandas as pd
import numpy as np
import logging
from analysis_module import process_results


# ---------------- LOGGER CONFIG ----------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # change to DEBUG for deep tracing

handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s"
)
handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(handler)


# ---------------- PRECOMPILED REGEX ----------------
SEAT_RE = re.compile(r"SEAT NO\.:\s*([A-Z0-9]+)")
NAME_RE = re.compile(r"NAME:\s*([A-Z\s]+?)\sMother")
SEM_RE = re.compile(r"SEMESTER\s*:\s*([1-8])", re.IGNORECASE)
SUBJECT_RE = re.compile(r"([A-Z0-9\-]+(?:_[A-Z]+)?)")

SGPA_RE = re.compile(
    r"(First|Second|Third|Fourth)\s+Semester\s+SGPA\s*:\s*([\d.]+|-----)\s*"
    r"Credits Earned/Total\s*:\s*(\d+)\s*/\s*(\d+)\s*"
    r"Total Credit Points\s*:\s*(\d+)",
    re.IGNORECASE
)


def result_analysis(pdf_path: str, subject_map: dict, semester, progress_callback=None):
    students = []

    roman_map = {
        1: "I", 2: "II", 3: "III", 4: "IV",
        5: "V", 6: "VI", 7: "VII", 8: "VIII"
    }

    semester_found = False

    logger.info("Starting result analysis")
    logger.info(f"PDF path: {pdf_path}")
    logger.info(f"Selected semester: {semester}")

    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            logger.info(f"Total pages detected: {total_pages}")

            for page_index, page in enumerate(pdf.pages, start=1):
                try:
                    text = page.extract_text()
                    if not text:
                        logger.warning(f"Page {page_index}: No text extracted")
                        continue

                    seat_match = SEAT_RE.search(text)
                    name_match = NAME_RE.search(text)

                    if not (seat_match and name_match):
                        logger.debug(f"Page {page_index}: Student info not found")
                        continue

                    sem_match = SEM_RE.search(text)
                    if not sem_match:
                        logger.debug(f"Page {page_index}: Semester not found")
                        continue

                    sem_digit = int(sem_match.group(1))
                    pdf_sem = f"Sem {roman_map[sem_digit]}"

                    if pdf_sem != semester:
                        logger.debug(
                            f"Page {page_index}: Semester mismatch ({pdf_sem})"
                        )
                        continue

                    semester_found = True

                    student_dict = {
                        "SEAT NUMBER": seat_match.group(1),
                        "STUDENT NAME": name_match.group(1).strip()
                    }

                    sem_text = text[sem_match.end():]

                    # -------- Subject marks extraction --------
                    for line in sem_text.splitlines():
                        line = line.strip()
                        if not line or "SGPA" in line or "Result" in line:
                            continue

                        subj_match = SUBJECT_RE.match(line)
                        if not subj_match:
                            continue

                        subject_code = subj_match.group(1)
                        if subject_code not in subject_map:
                            continue

                        tokens = line[len(subject_code):].split()
                        marks = []

                        for i, token in enumerate(tokens[:12]):
                            if i == 0 or tokens[i - 1] not in {"P", "*"}:
                                continue

                            if token == "AAA":
                                marks.append("AAA")
                                continue

                            token = token.replace("$", "").replace("#", "")
                            if token.isdigit():
                                marks.append(int(token))

                        if marks:
                            if len(marks) == 1:
                                marks.append(np.nan)
                            student_dict[subject_code] = marks

                    # -------- SGPA & credit summary --------
                    for sem, sgpa, earned, total, points in SGPA_RE.findall(text):
                        key = sem.lower()
                        student_dict[f"{key}_sgpa"] = (
                            None if sgpa == "-----" else float(sgpa)
                        )
                        student_dict[f"{key}_credits_earned"] = int(earned)
                        student_dict[f"{key}_credits_total"] = int(total)
                        student_dict[f"{key}_total_credit_points"] = int(points)

                    students.append(student_dict)
                    logger.info(
                        f"Page {page_index}: Processed student "
                        f"{student_dict['SEAT NUMBER']}"
                    )

                    if progress_callback:
                        progress_callback(page_index, total_pages)

                except Exception as page_error:
                    logger.warning(
                        f"Page {page_index}: Error while processing",
                        exc_info=page_error
                    )
                    continue

    except Exception as pdf_error:
        logger.error("Failed to open or read PDF", exc_info=pdf_error)
        raise RuntimeError(f"Failed to read PDF file: {pdf_error}")

    if not semester_found:
        logger.error("Selected semester not found in PDF")
        raise ValueError("Selected semester does not match the uploaded PDF")

    df = pd.DataFrame(students)
    if df.empty:
        logger.warning("No student records extracted")
        return df, 0

    df = process_results(df, subject_map, semester)
    logger.info(f"Result analysis completed. Students processed: {len(df)}")

    return df, len(df)
