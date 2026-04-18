import streamlit as st
import pdfplumber
import re

def extract_qa_from_text(full_text):
    """
    Splits an exam paper into questions and solutions using various possible headings.
    It automatically detects how many questions there are.
    """
    extracted_data = []
    
    # Step 1: Split the text based on possible headings
    # We use | (OR) to look for different heading variations. 
    # \b ensures we match the whole word
    split_pattern = r'\b(?:HINTS AND SOLUTIONS|ANSWERS|SOLUTIONS)\b'
    sections = re.split(split_pattern, full_text, flags=re.IGNORECASE)
    
    # If the document doesn't have any of these headings, return an error message
    if len(sections) < 2:
        return [{"question": "Format Error", "solution": "Could not find an Answers/Solutions section in this PDF."}]
        
    # We join all sections EXCEPT the last one as the questions. 
    questions_half = "".join(sections[:-1])
    # The very last section is guaranteed to be our actual solutions block
    solutions_half = sections[-1]
    
    # Step 2: Loop through numbers dynamically
    i = 1
    while True: 
        next_i = i + 1
        
        # --- Extract the Question ---
        q_pattern_current = r'\b' + str(i) + r'\.'
        q_pattern_next = r'\b' + str(next_i) + r'\.'
        
        q_match_current = re.search(q_pattern_current, questions_half)
        
        # If we can't find question 'i', we reached the end of the test!
        if not q_match_current:
            break 
            
        q_match_next = re.search(q_pattern_next, questions_half)
        
        # Cut the text for this specific question
        start_q = q_match_current.start()
        end_q = q_match_next.start() if q_match_next else len(questions_half)
        question_text = questions_half[start_q:end_q].strip()
        
        # --- Extract the Solution ---
        # Solutions might start with "1." or "1(" or "1 (" so we check for variations
        s_pattern_current = r'\b' + str(i) + r'\s*(?:\.|\()'
        s_pattern_next = r'\b' + str(next_i) + r'\s*(?:\.|\()'
        
        s_match_current = re.search(s_pattern_current, solutions_half)
        s_match_next = re.search(s_pattern_next, solutions_half)
        
        if s_match_current:
            start_s = s_match_current.start()
            end_s = s_match_next.start() if s_match_next else len(solutions_half)
            solution_text = solutions_half[start_s:end_s].strip()
        else:
            solution_text = "Solution not found for this question."
            
        # Step 3: Add the matched pair to our list
        extracted_data.append({
            "question": question_text,
            "solution": solution_text
        })
        
        # Increase our counter by 1 to check the next question
        i += 1
        
    return extracted_data


# --- WEB APP INTERFACE ---

# 1. Set the title of the web page
st.title("📄 PDF Question & Solution Extractor")
st.write("Upload a PDF document below to automatically extract questions and answers.")

# 2. Create a file uploader widget
uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

# 3. Process the file if the user has uploaded one
if uploaded_file is not None:
    st.info("Processing your PDF... please wait.")
    
    full_text = ""
    try:
        # Read the uploaded PDF file
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
                    
        # Run our extraction function
        results = extract_qa_from_text(full_text)
        
        # 4. Display the results on the web page
        if results and results[0]["question"] != "Format Error":
            st.success(f"Successfully extracted {len(results)} questions!")
            
            # Loop through results and display them nicely
            for i, item in enumerate(results, 1):
                st.subheader(f"Question {i}")
                st.write(item["question"])
                
                # Make the solution stand out
                st.markdown("**Solution:**")
                st.info(item["solution"]) 
                
                st.divider() # Adds a nice horizontal line between items
                
        elif results and results[0]["question"] == "Format Error":
            st.error(results[0]["solution"])
        else:
            st.warning("Could not find any questions matching the expected format.")
            
    except Exception as e:
        st.error(f"An error occurred while reading the PDF: {e}")
