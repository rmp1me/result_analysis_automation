# -------------------------------
# result_analysis.py
# -------------------------------
import pandas as pd
import numpy as np
import ast


def safe_int(value):
    """Safely convert value to int, else return None"""
    try:
        return int(value)
    except Exception:
        return None


def evaluate_subject(marks):
    """
    Input : [insem, endsem] OR string "[insem, endsem]"
    Output: [insem, endsem, PASS/FAIL]
    """

    # Empty / missing
    if marks is None or (isinstance(marks, str) and not marks.strip()):
        return [np.nan, np.nan, np.nan]

    # Convert string list to Python list
    if isinstance(marks, str):
        try:
            marks = ast.literal_eval(marks)
        except Exception:
            return [np.nan, np.nan, np.nan]

    # Validate structure
    if not isinstance(marks, (list, tuple)) or len(marks) != 2:
        return [np.nan, np.nan, np.nan]

    insem_raw, endsem_raw = marks

    # Absent case
    if endsem_raw == "AAA":
        return [insem_raw, endsem_raw, "FAIL"]

    insem = safe_int(insem_raw)
    endsem = safe_int(endsem_raw)

    if insem is None or endsem is None:
        return [insem, endsem, "FAIL"]

    result = "PASS" if insem >= 12 and endsem >= 28 else "FAIL"
    return [insem, endsem, result]


def process_results(df, subject_map):
    """
    Expands subject columns present in subject_map into:
    SUBJECT_INSEM, SUBJECT_ENDSEM, SUBJECT_RESULT
    """

    # SGPA / credit columns (kept at end)
    tail_columns = [
        col for col in df.columns
        if "sgpa" in col.lower() or "credit" in col.lower()
    ]

    # ONLY subjects present in JSON
    subject_columns = [col for col in df.columns if str(col) in subject_map]

    derived_columns = []

    for subject in subject_columns:
        expanded = df[subject].apply(evaluate_subject).to_list()

        insem_col = f"{subject}_INSEM"
        endsem_col = f"{subject}_ENDSEM"
        result_col = f"{subject}_RESULT"

        df[[insem_col, endsem_col, result_col]] = pd.DataFrame(
            expanded, index=df.index
        )

        derived_columns.extend([insem_col, endsem_col, result_col])

    # Remove original subject columns
    df.drop(columns=subject_columns, inplace=True)

    # Final column order
    base_columns = [
        col for col in df.columns
        if col not in derived_columns and col not in tail_columns
    ]

    df = df[base_columns + derived_columns + tail_columns]
    return df
