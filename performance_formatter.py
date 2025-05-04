from standard_labels import STANDARD_DETAILS
import pandas as pd
import streamlit as st


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

        details = STANDARD_DETAILS.get(standard_code, {"label": standard_code, "category": "Other", "student_label": standard_code})
        label = details.get("student_label", standard_code)
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

        display_label = f"{label} ({standard_code})"
        result[category].append((display_label, standard_code, score, emoji))

    return result


def build_tiered_standard_selectbox(formatted_performance, categories):
    """
    Returns the selected standard from a tiered selectbox grouped by category and performance level.
    """
    tier_order = [("🔴 Needs Support", 0, 60), ("🟡 Approaching", 60, 80), ("🟢 Strong", 80, 101)]
    sorted_standard_choices = []

    for tier_label, low, high in tier_order:
        for category in categories:
            standards_in_category = [
                (STANDARD_DETAILS[code].get("student_label", label), code, score, emoji)
                for label, code, score, emoji in formatted_performance[category]
                if low <= score < high
            ]
            if standards_in_category:
                sorted_standard_choices.append(("📂 " + category + f" ({tier_label})", None))
                for student_label, code, score, emoji in standards_in_category:
                    display = f"{emoji} {student_label} ({code}) — {score}%"
                    sorted_standard_choices.append((display, code))

    # Build selectbox options from above
    options_only = [label for label, code in sorted_standard_choices if code]
    display_to_code = {label: code for label, code in sorted_standard_choices if code}

    st.markdown("### 📝 Select a standard to practice")
    selected_display = st.selectbox("Organized by tier and category", options_only)
    return display_to_code[selected_display]