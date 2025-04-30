import random
import json
import os
import re
import streamlit as st
from openai import OpenAI

# Try to get API key from Streamlit secrets or environment variable
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except:
    api_key = os.getenv("OPENAI_API_KEY")

# Initialize the OpenAI client
client = openai.OpenAI(api_key=api_key)

def validate_answer(user_answer, correct_answer, answer_type):
    """
    Validates user answers against correct answers with more flexibility
    """
    if answer_type == "numeric":
        try:
            # Convert both to floats for numeric comparison
            user_numeric = float(user_answer.strip())
            correct_numeric = float(correct_answer.strip())
            
            # Allow for small floating point differences
            tolerance = 0.001
            return abs(user_numeric - correct_numeric) < tolerance
        except ValueError:
            # Try to extract numeric values from text answers
            try:
                # Extract all numbers from the user's answer
                user_numbers = [float(n) for n in re.findall(r'\d+\.?\d*', user_answer)]
                correct_numbers = [float(n) for n in re.findall(r'\d+\.?\d*', correct_answer)]
                
                # If we have the same number of values, compare them
                if len(user_numbers) == len(correct_numbers):
                    # Sort numbers for comparison when order doesn't matter
                    user_numbers.sort()
                    correct_numbers.sort()
                    
                    # Check if all numbers match within tolerance
                    return all(abs(u - c) < 0.001 for u, c in zip(user_numbers, correct_numbers))
            except:
                pass
            return False
    else:  # text answers
        # Normalize both answers: lowercase, remove extra spaces
        user_text = " ".join(user_answer.lower().split())
        correct_text = " ".join(correct_answer.lower().split())
        
        # Try exact match first
        if user_text == correct_text:
            return True
            
        # Extract key numbers/values for comparison
        try:
            user_numbers = [float(n) for n in re.findall(r'\d+\.?\d*', user_answer)]
            correct_numbers = [float(n) for n in re.findall(r'\d+\.?\d*', correct_answer)]
            
            # If we have the same numbers, it's probably correct
            if set(user_numbers) == set(correct_numbers):
                return True
        except:
            pass
            
        return False


def generate_multiple_choice_options(correct_answer, answer_type, question_data=None):
    """
    Generates plausible multiple choice options based on answer type
    """
    # Use a fixed seed based on the question content to ensure the same options
    # are generated for the same question
    if question_data:
        seed_str = question_data["question_text"] + str(correct_answer)
        random.seed(hash(seed_str) % (2**32))

    # Convert the correct answer to the appropriate type for comparison
    if answer_type == "numeric":
        try:
            correct = float(correct_answer)
            correct_rounded = round(correct,2) # Round for comparison
            
            # Common math error distractors - based on typical mistake patterns
            options = []
            
            # Add sign error
            options.append(-correct if correct != 0 else 1)
            
            # Add computation errors (typical +/- 1 or 2 errors)
            options.extend([correct + random.choice([-2, -1, 1, 2]) for _ in range(2)])
            
            # Add a different magnitude error (×10 or ÷10)
            options.append(correct * 10 if abs(correct) < 1 else correct / 10)
            
            # Round all options to make them cleaner
            options = [round(opt, 2) for opt in options]
            
            # Remove any distractors that equal the correct answer
            options = [opt for opt in options if abs(opt - correct_rounded) > 0.001]

            # Remove duplicates while preserving order
            unique_options = []
            for o in options:
                if o not in unique_options:
                    unique_options.append(o)
            
            # Take first 3 unique options
            unique_options = unique_options[:3]
            
            # If we don't have enough options, add some random ones
            while len(unique_options) < 3:
                new_opt = round(correct + random.uniform(-5, 5), 2)
                if abs(new_opt - correct_rounded) > 0.001 and new_opt not in unique_options:
                    unique_options.append(new_opt)

            # Final options including the correct answer
            options = [correct_rounded] + unique_options
                    
        except ValueError:
            # Fallback for non-convertible values
            options = [correct_answer, "Error option 1", "Error option 2", "Error option 3"]
    
    else:  # text options - request GPT to generate plausible distractors
        try:
            # For text answers, use GPT to generate plausible wrong answers
            distractor_prompt = (
                f"Question: {question_data['question_text']}\n"
                f"Correct answer: {correct_answer}\n\n"
                f"Generate 3 plausible but incorrect answers that a student might choose, "
                f"based on common misconceptions or errors. Format as a JSON object with a key 'distractors' containing an array."
            )
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": distractor_prompt}],
                temperature=0.3,
                max_tokens=800,
                response_format={"type": "json_object"}
            )
            
            distractors_content = response.choices[0].message.content
            distractors = json.loads(distractors_content)["distractors"]
            options = [correct_answer] + distractors

        except Exception as e:
            print(f"Error generating distractors: {e}")
            # Fallback options
            options = [correct_answer, "Incorrect option 1", "Incorrect option 2", "Incorrect option 3"]
    
    # Shuffle options to randomize position of correct answer
    random.shuffle(options)

    # Reset the random seed after we're done
    random.seed(None)

    return options