import streamlit as st
import pdfplumber
import re

def extract_qa_from_text(full_text):
    """
    Takes a full string of text and splits it into questions and solutions.
    """
    extracted_data = []
    qa_blocks = re.split(r'\b(?:Question|Q)\s*\d*\s*[:\.]', full_text, flags=re.IGNORECASE)
    
    for block in qa_blocks:
        if not block.strip():
            continue 
        
        parts = re.split(r'\b(?:Solution|Answer|Ans)\s*[:\.]', block, flags=re.IGNORECASE)
        
        if len(parts) >= 2:
            question_text = parts[0].strip()
            solution_text = " ".join(parts[1:]).strip() 
            extracted_data.append({"question": question_text, "solution": solution_text})
        else:
            extracted_data.append({"question": parts[0].strip(), "solution": "No solution found."})

    return extracted_data

# --- WEB APP INTERFACE ---

st.title("📄 PDF Question & Solution Extractor")
st.write("Upload a PDF document below to automatically extract questions and answers.")

uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file is not None:
    st.info("Processing your PDF... please wait.")
    
    full_text = ""
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
                    
        results = extract_qa_from_text(full_text)
        
        if results:
            st.success(f"Successfully extracted {len(results)} items!")
            
            for i, item in enumerate(results, 1):
                st.subheader(f"Question {i}")
                st.write(item["question"])
                st.markdown("**Solution:**")
                st.write(item["solution"])
                st.divider()
        else:
            st.warning("Could not find any questions or solutions matching the expected format.")
            
    except Exception as e:
        st.error(f"An error occurred while reading the PDF: {e}")
