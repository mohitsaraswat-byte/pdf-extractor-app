import streamlit as st
import google.generativeai as genai
import json
import os
import tempfile

# --- 1. CONFIGURE THE AI API ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except KeyError:
    st.error("API Key not found! Please add GEMINI_API_KEY to your Streamlit Secrets.")

def extract_qa_with_ai(pdf_file_path):
    """
    Uploads the actual PDF file directly to Gemini so it can "see" the 
    tables, graphs, and formatting perfectly.
    """
    # Using the latest 2.5 Flash model for the best vision and speed
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    try:
        # Step 1: Upload the file directly to Google's servers
        uploaded_pdf = genai.upload_file(pdf_file_path)
        
        # Step 2: The hyper-specific prompt
        prompt = """
        You are an expert data extraction assistant. I have uploaded a raw PDF of an exam paper. 
        It contains questions in the first half and a "Hints and Solutions" or "Answers" section at the end.
        
        Your strict instructions:
        1. Extract EVERY single question and match it with its EXACT corresponding solution.
        2. Exact Numbering: Create a "question_number" field. Preserve the EXACT numbering format used in the paper (e.g., "1.", "1(a)", "II.").
        3. Complete Content: Extract the ENTIRE question and solution. 
           - For MCQs, include all options (A, B, C, D) exactly as they appear.
           - For "Match the Following", extract the complete table data clearly.
           - For graphs or diagrams, describe the visual elements in detail or extract the text inside them. Do not summarize; capture every minute detail.
        4. Return the output STRICTLY as a valid JSON array of objects.
        
        The JSON must look exactly like this format:
        [
          {
            "question_number": "1(i)", 
            "question": "Which of the following areas receives rain from the North-East Monsoon?\n(A) Konkan coast\n(B) Ganga basin\n(C) Coromandel coast\n(D) Malabar coast", 
            "solution": "(C)\nThe Northeast monsoon brings rainfall to the Coromandel Coast."
          }
        ]
        
        Do not include any markdown formatting like ```json or any other conversational text. Return ONLY the raw JSON array.
        """
        
        # Step 3: Ask the AI to look at the PDF and read the prompt
        response = model.generate_content([prompt, uploaded_pdf])
        
        # Step 4: Clean up (delete the file from Google's servers)
        genai.delete_file(uploaded_pdf.name)
        
        # Step 5: Process the JSON
        json_string = response.text.strip()
        if json_string.startswith("```json"):
            json_string = json_string[7:-3].strip()
            
        extracted_data = json.loads(json_string)
        return extracted_data
        
    except Exception as e:
        return [{"question_number": "Error", "question": "AI Processing Error", "solution": f"The AI encountered an error: {e}"}]


# --- WEB APP INTERFACE ---

st.title("🤖 Advanced AI PDF Extractor")
st.write("Upload a PDF document. Our AI will visually read the document to capture precise numbering, MCQs, tables, and graphs!")

uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file is not None:
    st.info("Uploading PDF to AI vision model... this usually takes 10-15 seconds.")
    
    # We must save the uploaded file temporarily so the AI can read it
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        temp_pdf.write(uploaded_file.read())
        temp_pdf_path = temp_pdf.name
        
    try:
        # Pass the file path to our AI function
        results = extract_qa_with_ai(temp_pdf_path)
        
        # Display the results
        if results and results[0].get("question") != "AI Processing Error":
            st.success(f"AI successfully extracted {len(results)} items!")
            
            for item in results:
                # Use the exact question number from the AI (fallback to "?" if missing)
                q_num = item.get("question_number", "?")
                st.subheader(f"Question {q_num}")
                
                # Using st.text to preserve the exact spacing of MCQs and tables
                st.text(item.get("question", "No question text found."))
                
                st.markdown("**Solution:**")
                st.info(item.get("solution", "No solution found.")) 
                
                st.divider() 
                
        else:
            st.error(results[0].get("solution"))
            
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        
    finally:
        # Always delete the temporary file from your Streamlit server to save space
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
