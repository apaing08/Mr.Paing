import streamlit as st
import pandas as pd
from firebase_auth import initialize_firebase, create_user, reset_password, get_students_with_accounts
import random
import string
from data_manager import load_student_data

def generate_secure_password(length=8):
    """Generate a secure password"""
    characters = string.ascii_letters + string.digits
    password = ''.join(random.choice(characters) for i in range(length))
    return password

def show_admin_login():
    """Show admin login form"""
    st.title("Teacher Admin Panel")
    
    with st.form("admin_login"):
        admin_password = st.text_input("Admin Password", type="password")
        submit = st.form_submit_button("Login")
    
    # In a real app, you would check against a securely stored admin password
    # For demo purposes, we're using a hardcoded password - NEVER do this in production
    if submit:
        if admin_password == st.secrets.get("ADMIN_PASSWORD", "teacher123"):  # Default fallback for demo
            st.session_state["admin_authenticated"] = True
            st.rerun()
        else:
            st.error("Invalid admin password")

def show_admin_panel():
    """Show the admin panel for managing student accounts"""
    st.title("Student Account Management")
    
    # Initialize Firebase
    try:
        db = initialize_firebase()
    except Exception as e:
        st.error(f"Failed to initialize Firebase: {e}")
        st.stop()
    
    # Load student data
    df = load_student_data("8th grade standards.xlsx")
    students = df["Student"].unique().tolist()
    
    # Get list of students with accounts
    students_with_accounts = get_students_with_accounts()
    
    # Create tabs for different admin functions
    tab1, tab2, tab3 = st.tabs(["Create Accounts", "Reset Passwords", "Bulk Operations"])
    
    with tab1:
        st.subheader("Create New Student Account")
        
        # Student selection with indicator for existing accounts
        student_options = []
        for student in students:
            has_account = student in students_with_accounts
            status = "✅" if has_account else "❌"
            student_options.append(f"{student} {status}")
        
        selected_student_with_status = st.selectbox(
            "Select Student (✅ = has account, ❌ = no account)", 
            student_options
        )
        
        # Extract actual student name without status indicator
        selected_student = selected_student_with_status.rsplit(' ', 1)[0]
        
        has_account = selected_student in students_with_accounts
        
        # Generate a random initial password (outside the form)
        if "temp_password" not in st.session_state:
            st.session_state["temp_password"] = generate_secure_password()
        
        # Add a button to generate a new password (outside the form)
        if st.button("Generate New Password", key="gen_new_pwd_1"):
            st.session_state["temp_password"] = generate_secure_password()
            st.rerun()
        
        with st.form("create_account_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                # Default username suggestion based on student name
                default_username = selected_student.lower().replace(" ", "")
                username = st.text_input("Username", value=default_username)
            
            with col2:
                password = st.text_input(
                    "Password", 
                    value=st.session_state["temp_password"]
                )
            
            submit_create = st.form_submit_button("Create Account")
        
        if submit_create:
            if has_account:
                st.warning(f"{selected_student} already has an account.")
            else:
                success, message = create_user(username, password, selected_student)
                if success:
                    st.success(f"Account created for {selected_student}!")
                    st.info(f"Username: {username} | Password: {password}")
                    st.session_state["temp_password"] = generate_secure_password()  # Reset for next use
                    
                    # Update local cache of students with accounts
                    students_with_accounts[selected_student] = True
                else:
                    st.error(message)
    
    with tab2:
        st.subheader("Reset Student Password")
        
        # Filter to only show students with accounts
        students_with_account_list = [s for s in students if s in students_with_accounts]
        
        if not students_with_account_list:
            st.warning("No students have accounts yet.")
        else:
            selected_student_for_reset = st.selectbox(
                "Select Student to Reset Password", 
                students_with_account_list
            )
            
            # Generate a random new password (outside the form)
            if "reset_password" not in st.session_state:
                st.session_state["reset_password"] = generate_secure_password()
            
            # Add a button to generate a new password (outside the form)
            if st.button("Generate New Password", key="gen_new_pwd_2"):
                st.session_state["reset_password"] = generate_secure_password()
                st.rerun()
            
            with st.form("reset_password_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    # Lookup the username for this student
                    # In a real app, you'd fetch this from Firebase
                    default_username = selected_student_for_reset.lower().replace(" ", "")
                    reset_username = st.text_input("Username", value=default_username, disabled=True)
                
                with col2:
                    new_password = st.text_input(
                        "New Password", 
                        value=st.session_state["reset_password"]
                    )
                
                submit_reset = st.form_submit_button("Reset Password")
            
            if submit_reset:
                success, message = reset_password(reset_username, new_password)
                if success:
                    st.success(f"Password reset for {selected_student_for_reset}!")
                    st.info(f"New password: {new_password}")
                    st.session_state["reset_password"] = generate_secure_password()  # Reset for next use
                else:
                    st.error(message)
    
    with tab3:
        st.subheader("Bulk Operations")
        
        st.write("Create accounts for all students without existing accounts")
        
        students_without_accounts = [s for s in students if s not in students_with_accounts]
        
        if not students_without_accounts:
            st.success("All students already have accounts!")
        else:
            st.info(f"{len(students_without_accounts)} students need accounts")
            
            # Use a button outside of forms
            if st.button("Create Accounts for All Students"):
                results = []
                
                with st.spinner("Creating accounts..."):
                    for student in students_without_accounts:
                        username = student.lower().replace(" ", "")
                        password = generate_secure_password()
                        
                        success, message = create_user(username, password, student)
                        
                        results.append({
                            "Student": student,
                            "Username": username,
                            "Password": password,
                            "Status": "Created" if success else "Failed",
                            "Message": message if not success else ""
                        })
                
                # Display results table
                results_df = pd.DataFrame(results)
                st.write("Account Creation Results:")
                st.dataframe(results_df)
                
                # Option to download as CSV
                csv = results_df.to_csv(index=False)
                st.download_button(
                    label="Download Account Details (CSV)",
                    data=csv,
                    file_name="student_accounts.csv",
                    mime="text/csv"
                )
    
    # Logout button
    if st.sidebar.button("Logout"):
        st.session_state["admin_authenticated"] = False
        st.rerun()

def main():
    # Initialize session state
    if "admin_authenticated" not in st.session_state:
        st.session_state["admin_authenticated"] = False
    
    # Show admin login or panel based on authentication status
    if not st.session_state["admin_authenticated"]:
        show_admin_login()
    else:
        show_admin_panel()

if __name__ == "__main__":
    main()