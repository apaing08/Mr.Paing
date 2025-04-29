import pandas as pd
import streamlit as st

def load_student_data(file_path):
    """Loads and cleans student data from Power BI export."""
    excel_data = pd.ExcelFile(file_path)
    sheet = excel_data.sheet_names[0]
    df_raw = excel_data.parse(sheet)

    # Drop fake header row
    df_cleaned = df_raw.drop(index=0).reset_index(drop=True)

    # Filter out non-student rows
    df_cleaned = df_cleaned[~df_cleaned[df_cleaned.columns[0]].isin(["Total", ""])]
    df_cleaned = df_cleaned[df_cleaned[df_cleaned.columns[0]].notna()]
    df_cleaned = df_cleaned[~df_cleaned[df_cleaned.columns[0]].astype(str).str.contains("Applied filters", case=False)]

    # Rename first column and clean names
    df_cleaned.rename(columns={df_cleaned.columns[0]: "Student"}, inplace=True)
    df_cleaned["Student"] = df_cleaned["Student"].str.replace(r"\s*\(.*?\)", "", regex=True)

    return df_cleaned


def save_question_result(student_name, standard, question_data, user_answer, is_correct):
    """
    Saves student response to a database or file
    """
    # Create a DataFrame structure for this session's data
    if "practice_history" not in st.session_state:
        st.session_state.practice_history = pd.DataFrame(
            columns=["timestamp", "student", "standard", "question", "user_answer", 
                     "correct_answer", "is_correct"]
        )
    
    # Append this question's data
    new_row = pd.DataFrame({
        "timestamp": [pd.Timestamp.now()],
        "student": [student_name],
        "standard": [standard],
        "question": [question_data["question_text"]],
        "user_answer": [user_answer],
        "correct_answer": [question_data["correct_answer"]],
        "is_correct": [is_correct]
    })
    
    st.session_state.practice_history = pd.concat([st.session_state.practice_history, new_row])
    
    # Optionally save to disk
    st.session_state.practice_history.to_csv("practice_history.csv", index=False)