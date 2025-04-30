from standard_labels import STANDARD_DETAILS
import pandas as pd


def format_student_performance(df, student_name):
    """
    Returns a dictionary grouped by category
    {category_name: list of (label, code, percent, emoji)}
    """
    student_row = df[df["Student"] == student_name].iloc[0]
    result = {}

    for standard_code, percent in student_row[1:].items():
        if standard_code not in STANDARD_DETAILS or pd.isna(percent):
            continue  # Skip unknown or non-standard columns or missing data
        
        details = STANDARD_DETAILS.get(standard_code, {"label": standard_code, "category": "Other"})
        label = details["label"]
        category = details["category"]
        score = round(percent * 100, 1)
        
        # Color coding
        if score >= 80:
            emoji = "🟢"
        elif score >= 60:
            emoji = "🟡"
        else:
            emoji = "🔴"

        if category not in result:
            result[category] = []
        
        result[category].append((label, standard_code, score, emoji))
    
    return result
