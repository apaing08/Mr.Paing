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


# --- Streamlit setup ---
st.set_page_config(page_title="Math Practice App", layout="centered")
st.title("📊 Mr. Paing's Dashboard")

# --- Load Data ---
df = load_student_data("8th grade standards.xlsx")

# --- UI: Select a student ---
student_name = st.selectbox("Choose a student", df["Student"].unique())
student_row = df[df["Student"] == student_name].iloc[0]

# --- Show Performance/ Organize By Category ---
threshold = 0.7
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

if "generating_question" not in st.session_state:
    st.session_state["generating_question"] = False

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
            try:
                rows = question_data["table"]
                if rows and all(isinstance(row, list) for row in rows):
                    df_table = pd.DataFrame(rows[1:], columns=rows[0])
                    st.table(df_table)
            except Exception as e:
                st.warning(f"⚠️ Unable to display table: {e}")

        # --- Render Line Graph if exists ---
        if question_data.get("graph"):
            graph = question_data["graph"]
            fig, ax = plt.subplots()
            ax.plot(graph["x"], graph["y"], marker='o')
            ax.set_title(graph.get("label", "Graph"))
            ax.set_xlabel("x")
            ax.set_ylabel("y")
            st.pyplot(fig)
        
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
