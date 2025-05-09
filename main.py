import streamlit as st
import pandas as pd
import random
import matplotlib.pyplot as plt

# Import from our utility modules
from data_manager import load_student_data, save_question_result
from question_gen import parse_question_json, generate_and_store_question
from answer_validation import validate_answer, generate_multiple_choice_options
from performance_formatter import format_student_performance, build_tiered_standard_selectbox
from standard_labels import STANDARD_DETAILS
from firebase_auth import authenticate_user, is_user_valid_for_student, initialize_firebase, get_students_with_accounts
from render_helpers import render_table, render_line_graph



# --- Session State Management ---
def init_session_state():
    """Initialize session state variables if they don't exist"""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "username" not in st.session_state:
        st.session_state["username"] = ""
    if "chosen_student" not in st.session_state:
        st.session_state["chosen_student"] = None
    if "login_attempts" not in st.session_state:
        st.session_state["login_attempts"] = 0
    if "generating_question" not in st.session_state:
        st.session_state["generating_question"] = False

def login(username, password, student_name):
    """Handle login process"""
    success, authenticated_student = authenticate_user(username, password)
    
    if success and authenticated_student == student_name:
        st.session_state["authenticated"] = True
        st.session_state["username"] = username
        st.session_state["chosen_student"] = student_name
        st.session_state["login_attempts"] = 0
        return True
    else:
        st.session_state["login_attempts"] += 1
        return False

def logout():
    """Handle logout process"""
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""
    st.session_state["chosen_student"] = None
    # Clear question-related session states
    for key in list(st.session_state.keys()):
        if key in ["question_raw", "mc_options_dict", "correct_letter", 
                   "answer_feedback", "user_answer", "selected_option"]:
            del st.session_state[key]

# --- Main App ---
def main():
    # Initialize Firebase
    try:
        initialize_firebase()
    except Exception as e:
        st.error(f"Failed to initialize Firebase: {e}")
        st.error("Please check your Firebase configuration.")
        st.stop()
    
    # --- Streamlit setup ---
    st.set_page_config(page_title="Math Practice App", layout="centered")
    
    # Initialize session state
    init_session_state()
    
    # --- Handle logout button in sidebar ---
    if st.session_state["authenticated"]:
        # with st.sidebar:
            st.write(f"👋 Welcome, {st.session_state['username']}!")
            if st.button("Logout"):
                logout()
                st.rerun()
    
    # --- Check authentication status ---
    if not st.session_state["authenticated"]:
        show_login_page()
    else:
        show_main_app()

def show_login_page():
    """Display the login page"""
    st.title("📊 Mr. Paing's Math App")
    
    # --- Load Data ---
    df = load_student_data("8th grade standards.xlsx")
    
    # Get list of students with accounts
    students_with_accounts = get_students_with_accounts()
    
    # --- UI: Select a student ---
    student_name = st.selectbox("Choose your name", df["Student"].unique())
    
    # Store selected student in session state (for persistence)
    if st.session_state["chosen_student"] != student_name:
        st.session_state["chosen_student"] = student_name
    
    # Check if student already has an account
    has_account = student_name in students_with_accounts
    
    st.write("---")
    st.subheader("Login")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")
    
    if submit_button:
        if not username or not password:
            st.error("Please enter both username and password")
        else:
            if login(username, password, student_name):
                st.success("Login successful!")
                st.rerun()
            else:
                st.error(f"Invalid username or password for {student_name}")
                if st.session_state["login_attempts"] >= 5:
                    st.warning("Too many failed attempts. Please contact your teacher if you forgot your login information.")
    
    # Instructions for students
    st.write("---")
    if has_account:
        st.info("Please log in with your username and password to access your math practice.")
    else:
        st.warning("You don't have an account yet. Please ask your teacher to create one for you.")
    
    # Teacher section (could be hidden behind another password in a real app)
    with st.expander("Teacher Access"):
        st.warning("This section is for teachers only.")
        #st.write("In a real implementation, this would be password protected or on a separate admin page.")

def show_main_app():
    """Display the main app once authenticated"""
    st.title("📊 Mr. Paing's Dashboard")
    
    # --- Load Data ---
    df = load_student_data("8th grade standards.xlsx")
    
    # Get student information
    student_name = st.session_state["chosen_student"]
    student_row = df[df["Student"] == student_name].iloc[0]
    
    # --- Show Performance/ Organize By Category ---
    st.subheader(f"📈 Performance for {student_name}")
    formatted_performance = format_student_performance(df, student_name)
    categories = sorted(formatted_performance.keys())
    for category in categories:
        with st.expander(f"📂 {category}", expanded=False):
            for label, code, score, emoji in formatted_performance[category]:
                student_friendly_label = f"{label}"
                st.markdown(f"{emoji} **{student_friendly_label}** — {score}%")
    
    selected_standard = build_tiered_standard_selectbox(formatted_performance, categories)
    
    # --- Select question mode ---
    question_mode = st.selectbox(
        "Choose the type of questions to practice:",
        ["Multiple Choice", "Short Response"]
    )
    
    # --- Generate a question
    if st.button("🎯 Generate Question", disabled=st.session_state.get("generating_question", False)):
        st.session_state["generating_question"] = True  # Disable button during processing

        with st.spinner("Generating your question..."):
            generate_and_store_question(selected_standard, question_mode)
            st.session_state["generating_question"] = False  # Re-enable button

        st.rerun()
    
    # --- Show Question ---
    if "question_raw" in st.session_state:
        st.subheader("📘 Practice Question")
        question_type = st.session_state["question_type"]
        
        # Parse the JSON response
        question_data = parse_question_json(st.session_state["question_raw"])
        
        if question_data:
            raw_text = question_data["question_text"]
            
            # Display using HTML to bypass markdown interpretation
            st.markdown(f"<p>{raw_text}</p>", unsafe_allow_html=True)
    
            # --- Render Table if exists ---
            if question_data.get("table"):
                render_table(question_data["table"])

            # --- Render Line Graph if exists ---
            if question_data.get("graph"):
                render_line_graph(question_data["graph"])
            
            if question_type == "multiple_choice":
                # Generate options only if they don't exist in session state
                if "mc_options_dict" not in st.session_state:
                    options = generate_multiple_choice_options(
                        question_data["correct_answer"], 
                        question_data["answer_type"],
                        question_data
                    )
    
                    # Display options with letter labels
                    option_labels = ["A", "B", "C", "D"]
                    labeled_options = dict(zip(option_labels, options))
    
                    # Store in session state
                    st.session_state["mc_options_dict"] = labeled_options
                
                else:
                    # Use the options from session state (reuse options)
                    labeled_options = st.session_state["mc_options_dict"]
                
                # Find correct letter only once
                if "correct_letter" not in st.session_state:
                    correct_letter = None
                    if question_data["answer_type"] == "numeric":
                        try:
                            correct_value = float(question_data["correct_answer"])
                            for k, v in labeled_options.items():
                                try:
                                    if abs(float(v) - correct_value) < 0.001:
                                        correct_letter = k
                                        break
                                except (ValueError, TypeError):
                                    continue
                        except (ValueError, TypeError):
                            pass
                
                    # For text answers or if numeric comparison failed
                    if correct_letter is None:
                        matches = [k for k, v in labeled_options.items() 
                                if str(v).strip() == str(question_data["correct_answer"]).strip()]
                        correct_letter = matches[0] if matches else option_labels[0]  # Fallback to first option
    
                    st.session_state["correct_letter"] = correct_letter
                
                else:
                    correct_letter = st.session_state["correct_letter"]
                
                # Use key to ensure radio button is reset
                selected = st.radio(
                    "Choose one:", 
                    [f"{k}) {v}" for k, v in labeled_options.items()],
                    index = None,
                    key="mc_selection"
                )
                
                if st.button("✅ Submit Answer"):
                    if selected is None:
                        st.error("❗ Please select an answer before submitting.")
                    else:
                        picked = selected.split(")")[0]
                        selected_answer = labeled_options[picked]
                        is_correct = picked == correct_letter
                        
                        # Store feedback in session state
                        st.session_state["answer_feedback"] = {
                            "is_correct": is_correct,
                            "correct_answer": f"{correct_letter}) {labeled_options[correct_letter]}",
                            "explanation": question_data['explanation']
                        }
                        
                        st.session_state["selected_option"] = picked
                        
                        # Save student's progress
                        save_question_result(
                            student_name, 
                            st.session_state["current_standard"], 
                            question_data, 
                            str(selected_answer), 
                            is_correct
                        )
                        
                        st.rerun()
                
                # Show feedback if available
                if "answer_feedback" in st.session_state:
                    if st.session_state["answer_feedback"]["is_correct"]:
                        st.success("🎉 Correct!")
                    else:
                        st.error(f"❌ Incorrect. Correct answer: {st.session_state['answer_feedback']['correct_answer']}")
                    
                    st.info(f"🧠 Explanation: {st.session_state['answer_feedback']['explanation']}")
            
            elif question_type == "free_response":
                # Initialize user answer if not present
                if "user_answer" not in st.session_state:
                    st.session_state["user_answer"] = ""
                
                user_input = st.text_input(
                    "Your answer:", 
                    key="free_response_input", 
                    value=st.session_state["user_answer"]
                )
                
                # Update session state when input changes
                st.session_state["user_answer"] = user_input
                
                if st.button("✅ Check Answer") and user_input:
                    is_correct = validate_answer(
                        user_input, 
                        question_data["correct_answer"],
                        question_data["answer_type"]
                    )
                    
                    # Store feedback in session state
                    st.session_state["answer_feedback"] = {
                        "is_correct": is_correct,
                        "correct_answer": question_data["correct_answer"],
                        "explanation": question_data["explanation"]
                    }
                    
                    # Save student's progress
                    save_question_result(
                        student_name, 
                        st.session_state["current_standard"], 
                        question_data, 
                        user_input, 
                        is_correct,
                    )
                    
                    st.rerun()
                
                # Show feedback if available
                if "answer_feedback" in st.session_state:
                    if st.session_state["answer_feedback"]["is_correct"]:
                        st.success("🎉 Correct!")
                    else:
                        st.error(f"❌ Incorrect. The correct answer is: {st.session_state['answer_feedback']['correct_answer']}")
                    
                    st.info(f"🧠 Explanation: {st.session_state['answer_feedback']['explanation']}")
        else:
            st.error("⚠️ Failed to generate a properly formatted question. Please try again.")

if __name__ == "__main__":
    main()
