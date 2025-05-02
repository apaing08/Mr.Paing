import os
import json
import random
import re
import streamlit as st
from openai import OpenAI

# Try to get API key from Streamlit secrets or environment variable
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except:
    api_key = os.getenv("OPENAI_API_KEY")

# Initialize the OpenAI client
client = OpenAI(api_key=api_key)

def generate_math_question(standard, variation_params=None, question_mode="Both"):
    """
    Generates a structured math question with specific variation parameters.
    """
    # Decide question type based on mode
    if question_mode == "Multiple Choice":
        question_type = "multiple_choice"
    elif question_mode == "Short Response":
        question_type = "free_response"
    else:
        question_type = random.choice(["multiple_choice", "free_response"])

    # Determine answer type
    if question_type == "multiple_choice":
        answer_type = random.choice(["numeric", "text"])
    else:
        answer_type = "mixed"  # For free response
    
    # Default variation parameters if none provided
    if variation_params is None:
        variation_params = {
            "difficulty": random.choice(["basic", "intermediate", "challenging"]),
            "context": random.choice(["abstract", "real-world", "visual"]),
            "approach": random.choice(["computational", "conceptual", "problem-solving"])
        }
    
    prompt = (
        f"Create a {variation_params['difficulty']} 8th-grade math question "
        f"as a {question_type.replace('_', ' ')} question aligned to standard {standard} "
        f"that would be similar to what students would see in the 8th Grade NYS Exam.\n"
        f"Use a {variation_params['context']} context and focus on {variation_params['approach']} skills.\n\n"
        f"IMPORTANT: Format your response as a clean, properly spaced JSON object with the following structure:\n"
        f"{{"
        f'"question_text": "Clear, properly spaced question text with no formatting errors",\n'
        f'"correct_answer": "The exact expected answer",\n' 
        f'"answer_type": "{answer_type}",\n'
        f'"explanation": "Step by step explanation with proper spacing",\n'
        f'"equation": "x + 5 = 10"  # The core equation if applicable, otherwise "none"\n'
        f"}}\n\n"
        f'"table": [["header1", "header2"], [row1val1, row1val2], ...] or null,\n'
        f'"graph": {{"x": [x1, x2, ...], "y": [y1, y2, ...], "label": "Graph title"}} or null\n'
        f"\n\n"
        f"Ensure all text is properly spaced with no run-together words.\n"
        f"For numeric answers, provide the exact value (e.g., 5, 3.14, -2).\n"
        f"For text answers, provide the exact expected text response.\n"
        f"Check that your output is valid JSON with no formatting errors before returning it."
        f"ONLY include either `table` or `graph`, not both. Use line graphs (not bar graphs).\n"
        f"Ensure your output is valid JSON. Do not include markdown formatting or comments."
    )

    try:
        # Updated to use the new OpenAI API format
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a specialized math education AI that outputs valid JSON formatted responses only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=4000,
            response_format={"type": "json_object"}  # Ensure structured output
        )
        
        # Updated to match the new response structure
        content = response.choices[0].message.content.strip()
        return content, question_type
    except Exception as e:
        return f"Error generating question: {e}", "error"


def generate_unique_question(standard, question_history=None, question_mode="Both"):
    """
    Generates a question that isn't too similar to previous questions.
    """
    if question_history is None:
        question_history = []
    
    # Try different variation combinations until we get a unique question
    attempts = 0
    max_attempts = 5
    
    while attempts < max_attempts:
        # Generate different parameter combinations
        variation_params = {
            "difficulty": random.choice(["basic", "intermediate", "challenging"]),
            "context": random.choice(["abstract", "real-world application", "visual representation", "data analysis"]),
            "approach": random.choice(["direct computation", "conceptual understanding", "problem-solving strategy", "pattern recognition"])
        }
        
        # Generate a question with these parameters
        raw_output, question_type = generate_math_question(standard, variation_params, question_mode)
        
        try:
            question_data = parse_question_json(raw_output)
            
            # Check if question is too similar to history
            if question_data:
                is_unique = True
                for past_question in question_history:
                    # Simple similarity check using text similarity
                    similarity = calculate_similarity(question_data["question_text"], past_question["question_text"])
                    if similarity > 0.7:  # If more than 70% similar
                        is_unique = False
                        break
                
                if is_unique:
                    return raw_output, question_type
        except:
            pass
        
        attempts += 1
    
    # If we couldn't generate a unique question, use the last attempt
    return raw_output, question_type

def calculate_similarity(text1, text2):
    """
    Calculate simple text similarity between two questions
    to avoid generating very similar questions
    """
    # Convert to lowercase and remove punctuation
    def normalize(text):
        return re.sub(r'[^\w\s]', '', text.lower())
    
    words1 = set(normalize(text1).split())
    words2 = set(normalize(text2).split())
    
    # Jaccard similarity
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    return intersection / union if union > 0 else 0

def parse_question_json(raw_output):
    """
    Robust parser for question JSON that handles various edge cases
    """
    try:
        # Check for error messages
        if isinstance(raw_output, str) and raw_output.startswith("Error generating question:"):
            try:
                # Try to use Streamlit's error function if we're in a Streamlit context
                st.error(f"⚠️ {raw_output}")
            except:
                # If not in a Streamlit context, just print the error
                print(f"⚠️ {raw_output}")
            return None
            

        # First attempt: direct parsing
        try:
            question_data = json.loads(raw_output)
        except json.JSONDecodeError:
            # If direct parsing fails, try to sanitize the string
            sanitized = raw_output.strip()
            
            # Make sure we're only getting a valid JSON object
            if sanitized.startswith('{') and '}' in sanitized:
                end_index = sanitized.rindex('}') + 1
                sanitized = sanitized[:end_index]
                
                try:
                    question_data = json.loads(sanitized)
                except:
                    # If still failing, this is likely not valid JSON
                    error_msg = "Could not parse response as JSON after sanitization"
                    try:
                        st.error(error_msg)
                    except:
                        print(error_msg)
                    raise ValueError(error_msg)
            else:
                error_msg = "Response does not contain a JSON object"
                try:
                    st.error(error_msg)
                except:
                    print(error_msg)
                raise ValueError(error_msg)
        
        # Validate and ensure required fields
        required_fields = ["question_text", "correct_answer", "answer_type", "explanation"]
        for field in required_fields:
            if field not in question_data:
                error_msg = f"Missing required field: {field}"
                try:
                    st.error(error_msg)
                except:
                    print(error_msg)
                raise ValueError(error_msg)
        
        # Add equation field if missing
        if "equation" not in question_data:
            question_data["equation"] = "none"

        if "table" not in question_data:
            question_data["table"] = None

        if "graph" not in question_data:
            question_data["graph"] = None
        
        return question_data
        
    except Exception as e:
        # Print error without relying on Streamlit
        error_msg = f"⚠️ Error parsing question data: {e}"
        try:
            st.error(error_msg)
        except:
            print(error_msg)
        print(f"Full raw content: {raw_output}")
        return None
