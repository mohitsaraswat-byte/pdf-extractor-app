import streamlit as st
import google.generativeai as genai
import json
import os
import tempfile

# --- 1. CONFIGURE THE AI API ---
# Ensure you have added GEMINI_API_KEY to your Streamlit Community Cloud Secrets
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except KeyError:
    st.error("API Key not found! Please add GEMINI_API_KEY to your Streamlit Secrets.")

def extract_qa_with_ai(pdf_file_path):
    """
    Uploads the PDF to Gemini 2.5 Flash for vision-based extraction,
    forcing strict Markdown formatting and line breaks.
    """
    # Using the latest 2.5 Flash model for speed, vision, and availability
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    try:
        # Step 1: Upload the file directly to Google's servers for vision processing
        uploaded_pdf = genai.upload_file(pdf_file_path)
        
        # Step 2: The hyper-specific PRODUCTION prompt
        prompt = """
        You are an expert data extraction assistant. I have uploaded a raw PDF of an exam paper. 
        It contains questions in the first half and a "Hints and Solutions" or "Answers" section at the end.
        
        Your STRICT instructions for PRODUCTION-READY formatting:
        1. Exact Numbering: Preserve the exact hierarchy (e.g., "11.(iv)", "2.(a)").
        2. STRICT LINE BREAKS (CRITICAL): 
           - Sub-questions like (A), (B), (C) or (i), (ii) MUST start on a brand new line. 
           - You MUST use double line breaks (\\n\\n) between subparts to ensure they are visually separated. NEVER merge them into a single paragraph.
           - If a solution contains a list (1., 2., 3. or bullet points), format it as a proper Markdown list. Do NOT append the next sub-question to the end of a list item.
           - Multiple choice options (A, B, C, D) must be placed on separate lines.
        3. PERFECT TABLES: If there is tabular data, you MUST format it using strict Markdown table syntax (with | and -). Do not return raw text for tables.
        4. Images & Graphs: You cannot extract actual images. If a question contains a graph, map, or diagram, insert a placeholder like "[IMAGE: Graph showing Elasticity of Supply]" and describe its contents briefly.
        5. Match every question with its EXACT corresponding solution.
        6. Return the output STRICTLY as a valid JSON array of objects.
        
        The JSON must look EXACTLY like this formatting example, paying close attention to the \\n\\n line breaks:
        [
          {
            "question_number": "11.(iv)", 
            "question": "(A) Why are roadways considered more significant than other means of transport?\\n\\n(B) What are the two advantages of using railways as a means of transport?", 
            "solution": "(A) Roadways are considered more important because:\\n\\n* Roads are easier and cheaper to construct.\\n* Roads can navigate steep slopes.\\n\\n(B) Two advantages of railways are:\\n\\n* Railways promote tourism.\\n* Railways efficiently handle large volumes of goods."
          }
        ]
        
        Do not include any markdown formatting like ```json outside the array. Return ONLY the raw JSON array.
        """
        
        # Step 3: Generate the content
        response = model.generate_content([prompt, uploaded_pdf])
        
        # Step 4: Delete the file from Google's servers to ensure privacy
        genai.delete_file(uploaded_pdf.name)
        
        # Step 5: Process and clean the JSON response
        json_string = response.text.strip()
        
        # Remove markdown code blocks if the AI accidentally added them
        if json_string.startswith("```json"):
            json_string = json_string[7:-3].strip()
        elif json_string.startswith("```"):
            json_string = json_string[3:-3].strip()
            
        extracted_data = json.loads(json_string)
        return extracted_data
        
    except json.JSONDecodeError as e:
         return [{"question_number": "Error", "question": "JSON Parsing Error", "solution": f"Failed to read the AI's response properly. Try again. Error: {e}\n\nRaw Output:\n{json_string}"}]
    except Exception as e:
        return [{"question_number": "Error", "question": "AI Processing Error", "solution": f"The AI encountered an error: {e}"}]


# --- WEB APP INTERFACE ---

st.set_page_config(page_title="AI PDF Extractor", page_icon="📄", layout="wide")

st.title("🤖 Production-Ready AI PDF Extractor")
st.write("Upload a PDF document. This tool handles complex formatting, sub-question line breaks, multiple-choice options, and Markdown tables flawlessly.")

uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file is not None:
    st.info("Uploading PDF to AI vision model... This takes about 10-20 seconds to process perfectly formatted text.")
    
    # Save the uploaded file temporarily so the AI can read it
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        temp_pdf.write(uploaded_file.read())
        temp_pdf_path = temp_pdf.name
        
    try:
        # Run the extraction
        results = extract_qa_with_ai(temp_pdf_path)
        
        # Display the results
        if results and results[0].get("question_number") != "Error":
            st.success(f"Successfully extracted and formatted {len(results)} items!")
            
            for item in results:
                q_num = item.get("question_number", "?")
                st.subheader(f"Question {q_num}")
                
                # We use st.markdown so that Tables, Lists, and \n\n breaks render perfectly
                st.markdown(item.get("question", "No question text found."))
                
                st.markdown("**Solution:**")
                st.info(item.get("solution", "No solution found.")) 
                
                st.divider() 
                
        else:
            # Display any errors that occurred
            st.error(results[0].get("question"))
            st.error(results[0].get("solution"))
            
    except Exception as e:
        st.error(f"An unexpected error occurred in the application: {e}")
        
    finally:
        # Always clean up the temporary file from the Streamlit server
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
