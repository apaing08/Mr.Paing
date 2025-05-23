import firebase_admin
from firebase_admin import credentials, auth, firestore
import streamlit as st
import os
import json

def initialize_firebase():
    """Initialize Firebase if not already initialized"""
    if not firebase_admin._apps:
        try:
            # Check if the Firebase credentials are in Streamlit secrets
            if "FIREBASE_SERVICE_ACCOUNT" in st.secrets:
                # Log successful finding of credentials (for debugging)
                #st.error("Firebase credentials found in Streamlit secrets")
                
                try:
                    # Try to parse the JSON string from secrets
                    service_account_info = json.loads(st.secrets["FIREBASE_SERVICE_ACCOUNT"])
                    cred = credentials.Certificate(service_account_info)
                except json.JSONDecodeError as e:
                    st.error(f"Failed to parse Firebase credentials JSON: {e}")
                    st.error("Please check your secrets.toml file format")
                    raise
            # If we're in local development and have a JSON file
            elif os.path.exists("firebase-key.json"):
                cred = credentials.Certificate("firebase-key.json")
            else:
                # No credentials found - raise a clear error
                st.error("No Firebase credentials found. Please add FIREBASE_SERVICE_ACCOUNT to your Streamlit secrets.")
                raise FileNotFoundError("Firebase credentials not found in secrets or as a local file")
                
            # Initialize Firebase with the credentials
            firebase_admin.initialize_app(cred)
            
        except Exception as e:
            st.error(f"Firebase initialization error: {e}")
            raise
    
    return firestore.client()

def authenticate_user(username, password):
    """Authenticate a user with Firebase Authentication"""
    try:
        initialize_firebase()
        # In a real implementation, you should use Firebase Authentication methods
        # Here we're using a simple approach with Firebase Firestore
        db = firestore.client()
        user_ref = db.collection('users').document(username).get()
        
        if user_ref.exists:
            user_data = user_ref.to_dict()
            # WARNING: In production, NEVER store raw passwords!
            # This is just for demonstration - you should use proper password hashing
            if user_data and user_data.get('password') == password:
                return True, user_data.get('student_name')
        
        return False, None
    except Exception as e:
        st.error(f"Authentication error: {e}")
        return False, None

def is_user_valid_for_student(username, student_name):
    """Check if the user is authorized to access this student's data"""
    try:
        db = firestore.client()
        user_ref = db.collection('users').document(username).get()
        
        if user_ref.exists:
            user_data = user_ref.to_dict()
            return user_data.get('student_name') == student_name
        
        return False
    except Exception as e:
        st.error(f"Authorization error: {e}")
        return False

def create_user(username, password, student_name):
    """Create a new user in Firestore"""
    try:
        db = firestore.client()
        user_ref = db.collection('users').document(username)
        
        # Check if username already exists
        if user_ref.get().exists:
            return False, "Username already exists"
        
        # Create the user document
        user_ref.set({
            'username': username,
            'password': password,  # WARNING: Should be hashed in production
            'student_name': student_name,
            'created_at': firestore.SERVER_TIMESTAMP
        })
        
        return True, "User created successfully"
    except Exception as e:
        return False, f"Error creating user: {e}"

def get_students_with_accounts():
    """Get a list of students who have accounts"""
    try:
        db = firestore.client()
        users = db.collection('users').stream()
        
        student_dict = {}
        for user in users:
            user_data = user.to_dict()
            student_name = user_data.get('student_name')
            if student_name:
                student_dict[student_name] = True
        
        return student_dict
    except Exception as e:
        st.error(f"Error getting students: {e}")
        return {}

def reset_password(username, new_password):
    """Reset a user's password"""
    try:
        db = firestore.client()
        user_ref = db.collection('users').document(username)
        
        if not user_ref.get().exists:
            return False, "User does not exist"
        
        # Update the password
        user_ref.update({
            'password': new_password  # WARNING: Should be hashed in production
        })
        
        return True, "Password reset successfully"
    except Exception as e:
        return False, f"Error resetting password: {e}"