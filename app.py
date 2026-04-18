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
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    try:
        uploaded_pdf = genai.upload_file(pdf_file_path)
        
        # We have completely upgraded the prompt to force Markdown and handle nesting
        prompt = """
        You are an expert data extraction assistant. I have uploaded a raw PDF of an exam paper. 
        It contains questions in the first half and a "Hints and Solutions" or "Answers" section at the end.
        
        Your strict instructions:
        1. Exact Numbering & Nesting: Preserve the EXACT hierarchy. If a question is "3.(iv)", label it exactly like that. If it has sub-questions like (A), (B), (C), keep them clearly structured within the question text using Markdown lists.
        2. PERFECT TABLES: If there is tabular data (like the Climate Data table), you MUST format it using strict, proper Markdown table syntax (with | and -). Do not return raw text for tables.
        3. Images & Graphs: You cannot output images. If a question contains a graph, map, or diagram, insert a placeholder like "[IMAGE: Graph showing Elasticity of Supply]" and describe its contents briefly.
        4. Match every question with its EXACT corresponding solution.
        5. Return the output STRICTLY as a valid JSON array of objects.
        
        The JSON must look exactly like this format:
        [
          {
            "question_number": "3.(iv)", 
            "question": "Study the climatic data given below and answer the questions that follow:\n\n| Month | Jan | Feb |\n|---|---|---|\n| Temp | 8.4 | 11.5 |\n\n(A) Calculate the annual range...\n(B) State whether...", 
            "solution": "(A) 32.6°C\n(B) Continental interior"
          }
        ]
        
        Do not include any markdown formatting like ```json outside the array. Return ONLY the raw JSON array.
        """
        
        response = model.generate_content([prompt, uploaded_pdf])
        genai.delete_file(uploaded_pdf.name)
        
        json_string = response.text.strip()
        if json_string.startswith("```json"):
            json_string = json_string[7:-3].strip()
            
        extracted_data = json.loads(json_string)
        return extracted_data
        
    except Exception as e:
        return [{"question_number": "Error", "question": "AI Processing Error", "solution": f"The AI encountered an error: {e}"}]


# --- WEB APP INTERFACE ---

st.title("🤖 Advanced AI PDF Extractor")
st.write("Upload a PDF document. Now supporting beautiful Markdown tables and exact nesting hierarchies!")

uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file is not None:
    st.info("Uploading PDF to AI vision model... this usually takes 10-15 seconds.")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        temp_pdf.write(uploaded_file.read())
        temp_pdf_path = temp_pdf.name
        
    try:
        results = extract_qa_with_ai(temp_pdf_path)
        
        if results and results[0].get("question") != "AI Processing Error":
            st.success(f"AI successfully extracted {len(results)} items!")
            
            for item in results:
                q_num = item.get("question_number", "?")
                st.subheader(f"Question {q_num}")
                
                # CRITICAL FIX: We changed st.text() to st.markdown() 
                # This makes the tables render beautifully as actual tables!
                st.markdown(item.get("question", "No question text found."))
                
                st.markdown("**Solution:**")
                st.info(item.get("solution", "No solution found.")) 
                
                st.divider() 
                
        else:
            st.error(results[0].get("solution"))
            
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        
    finally:
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
