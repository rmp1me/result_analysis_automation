import pandas as pd
import numpy as np
import ast

def evaluate_subject(marks):
    """
    Input  : [insem, endsem] OR string "[insem, endsem]"
    Output : insem, endsem
    """
    if marks is None or (isinstance(marks, str) and not marks.strip()):
        return [np.nan, np.nan]

    if isinstance(marks, str):
        try:
            marks = ast.literal_eval(marks)
        except Exception:
            return [np.nan, np.nan]

    if not isinstance(marks, (list, tuple)) or len(marks) != 2:
        return [np.nan, np.nan]

    return marks[0], marks[1]


# =====================================================
# NORMALIZE SUBJECT COLUMNS 
# =====================================================
def normalize_subject_columns(df: pd.DataFrame, subject_map: dict) -> pd.DataFrame:
    """
    Converts legacy subject columns:
        210241 -> [insem, endsem]
    into:
        210241_INSEM, 210241_ENDSEM

    Runs ONLY if *_INSEM columns do not already exist.
    """

    # Already normalized → skip
    if any(col.endswith("_INSEM") for col in df.columns):
        return df

    subject_codes = set(subject_map.keys())
    subject_columns = [c for c in df.columns if str(c) in subject_codes]

    if not subject_columns:
        return df

    tail_columns = [
        c for c in df.columns
        if "sgpa" in c.lower() or "credit" in c.lower()
    ]

    derived_columns = []

    for subject in subject_columns:
        expanded = df[subject].apply(evaluate_subject).to_list()

        insem_col = f"{subject}_INSEM"
        endsem_col = f"{subject}_ENDSEM"

        df[[insem_col, endsem_col]] = pd.DataFrame(
            expanded, index=df.index
        )

        derived_columns.extend([insem_col, endsem_col])

    df.drop(columns=subject_columns, inplace=True)

    base_columns = [
        c for c in df.columns
        if c not in derived_columns and c not in tail_columns
    ]

    df = df[base_columns + derived_columns + tail_columns]
    return df


# =====================================================
# CLEAN MARKS COLUMN
# =====================================================
def clean_marks_column(df: pd.DataFrame, col_name: str) -> pd.Series:
    return df[col_name].apply(
        lambda x: "AAA" if str(x).strip().upper() == "AAA"
        else pd.to_numeric(x, errors="coerce")
    )


# =====================================================
# AUTO-DETECT RESULT COLUMN
# =====================================================
def get_result_column(df: pd.DataFrame, code: str):
    for suffix in ["_RESULT", "_RESULT_CALC"]:
        col = f"{code}{suffix}"
        if col in df.columns:
            return col
    return None


# =====================================================
# STEP 1: ADD TOTAL COLUMNS
# =====================================================
def add_total_columns(df: pd.DataFrame, subject_codes: list) -> pd.DataFrame:
    for code in subject_codes:
        insem_col = f"{code}_INSEM"
        endsem_col = f"{code}_ENDSEM"
        total_col = f"{code}_TOTAL"

        if insem_col not in df.columns and endsem_col not in df.columns:
            continue

        if insem_col in df.columns:
            df[insem_col] = clean_marks_column(df, insem_col)
        if endsem_col in df.columns:
            df[endsem_col] = clean_marks_column(df, endsem_col)

        total_vals = np.where(
            (df.get(insem_col) == "AAA") & (df.get(endsem_col) == "AAA"),
            np.nan,
            pd.to_numeric(df.get(insem_col), errors="coerce").fillna(0)
            + pd.to_numeric(df.get(endsem_col), errors="coerce").fillna(0)
        )

        if total_col in df.columns:
            df.drop(columns=[total_col], inplace=True)

        insert_after = endsem_col if endsem_col in df.columns else insem_col
        idx = df.columns.get_loc(insert_after)
        df.insert(idx + 1, total_col, total_vals)

    return df


# =====================================================
# STEP 2: RESULT FIX (SPPU RULE)
# =====================================================
def auto_fix_result_from_total(df: pd.DataFrame, subject_codes: list) -> pd.DataFrame:
    for code in subject_codes:
        insem_col = f"{code}_INSEM"
        endsem_col = f"{code}_ENDSEM"
        total_col = f"{code}_TOTAL"

        if total_col not in df.columns or endsem_col not in df.columns:
            continue

        result_col = get_result_column(df, code)
        if not result_col:
            result_col = f"{code}_RESULT"
            idx = df.columns.get_loc(total_col)
            df.insert(idx + 1, result_col, np.nan)

        df[result_col] = np.where(
            (df[insem_col] == "AAA") & (df[endsem_col] == "AAA"),
            "ABSENT",
            np.where(
                df[endsem_col] == "AAA",
                "FAIL",
                np.where(df[total_col] >= 40, "PASS", "FAIL")
            )
        )

    return df


# =====================================================
# ANALYSIS FUNCTIONS
# =====================================================
def get_total_pass_fail(df: pd.DataFrame) -> dict:
    result_cols = [c for c in df.columns if c.endswith("_RESULT")]

    def is_all_pass(row):
        vals = row[result_cols].dropna()
        return len(vals) > 0 and (vals == "PASS").all()

    total = len(df)
    passed = df.apply(is_all_pass, axis=1).sum()

    return {
        "Total Appeared": total,
        "Total Passed": passed,
        "Total Failed": total - passed,
        "Pass Percentage": round((passed / total) * 100, 2)
    }


def get_subject_wise_result(df: pd.DataFrame, subject_map: dict) -> pd.DataFrame:
    rows = []

    for code, subject in subject_map.items():
        result_col = get_result_column(df, code)
        endsem_col = f"{code}_ENDSEM"

        if not result_col or endsem_col not in df.columns:
            continue

        appeared = (df[endsem_col] != "AAA").sum()
        absent = (df[endsem_col] == "AAA").sum()
        passed = (df[result_col] == "PASS").sum()
        failed = (df[result_col] == "FAIL").sum()

        rows.append({
            "Subject": subject,
            "Students Appeared": appeared,
            "Students Passed": passed,
            "Students Failed": failed,
            "Students Absent": absent,
            "% of Passing": round((passed / appeared) * 100, 2) if appeared else 0
        })

    df_out = pd.DataFrame(rows)
    df_out.insert(0, "Sr.No.", range(1, len(df_out) + 1))
    return df_out


def get_subject_toppers(df: pd.DataFrame, subject_map: dict) -> pd.DataFrame:
    rows = []

    for code, subject in subject_map.items():
        result_col = get_result_column(df, code)
        total_col = f"{code}_TOTAL"

        if not result_col or total_col not in df.columns:
            continue

        passed_df = df[(df[result_col] == "PASS") & (df[total_col] >= 40)]
        if passed_df.empty:
            continue

        max_marks = passed_df[total_col].max()
        toppers = passed_df[passed_df[total_col] == max_marks]

        for _, r in toppers.iterrows():
            rows.append({
                "Subject": subject,
                "Seat Number": r["SEAT NUMBER"],
                "Student Name": r["STUDENT NAME"],
                "Marks": max_marks
            })

    return pd.DataFrame(rows)


def get_top_5_rankers(df: pd.DataFrame) -> pd.DataFrame:
    result_cols = [c for c in df.columns if c.endswith("_RESULT")]

    def all_clear(row):
        vals = row[result_cols].dropna()
        return len(vals) > 0 and (vals == "PASS").all()

    df_clear = df[df.apply(all_clear, axis=1)].copy()
    if df_clear.empty:
        return pd.DataFrame()

    sgpa_cols = [c for c in df.columns if c.lower().endswith("_sgpa")]
    df_clear["RANK_SCORE"] = df_clear[sgpa_cols].mean(axis=1, skipna=True)

    df_clear = df_clear.sort_values("RANK_SCORE", ascending=False)
    df_clear["Rank"] = range(1, len(df_clear) + 1)

    cols = ["Rank", "SEAT NUMBER", "STUDENT NAME"] + sgpa_cols + ["RANK_SCORE"]
    return df_clear.head(5)[[c for c in cols if c in df_clear.columns]]


# =====================================================
# MAIN ENTRY (CALLED FROM extractor.py)
# =====================================================
def process_results(df: pd.DataFrame, subject_map: dict,semester) -> pd.DataFrame:
    df = normalize_subject_columns(df, subject_map)

    subject_codes = list(subject_map.keys())
    df = add_total_columns(df, subject_codes)
    df = auto_fix_result_from_total(df, subject_codes)

    # Reports
    overall = get_total_pass_fail(df)
    subject_df = get_subject_wise_result(df, subject_map)
    topper_df = get_subject_toppers(df, subject_map)
    rank_df = get_top_5_rankers(df)

    overall_df = pd.DataFrame(overall.items(), columns=["Metric", "Value"])

    with pd.ExcelWriter(f"Final_Result_Report_{semester}.xlsx", engine="xlsxwriter") as writer:
        overall_df.to_excel(excel_writer=writer, sheet_name=f"Overall_Result_{semester}", index=False)
        subject_df.to_excel(excel_writer=writer, sheet_name=f"Subject_Wise_Result_{semester}", index=False)
        topper_df.to_excel(excel_writer=writer, sheet_name=f"Subject_Toppers_{semester}", index=False)
        rank_df.to_excel(excel_writer=writer, sheet_name=f"Top_5_Rankers_{semester}", index=False)
        df.to_excel(excel_writer=writer, sheet_name=f"Processed_Result_{semester}", index=False)

    return df

