import streamlit as st
import pdfplumber
import google.generativeai as genai
import json

# --- 1. CONFIGURE THE AI API ---
# Streamlit safely grabs your secret key from the settings we just configured
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except KeyError:
    st.error("API Key not found! Please add GEMINI_API_KEY to your Streamlit Secrets.")

def extract_qa_with_ai(full_text):
    """
    Sends the messy PDF text to the Gemini API and asks it to organize it 
    into a perfect list of questions and solutions.
    """
    # We use the 'flash' model because it is incredibly fast and cost-effective
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    # This is our specific instruction to the AI
    prompt = f"""
    You are an expert data extraction assistant. I will provide you with the raw text from an exam paper. 
    It contains questions in the first half and a "Hints and Solutions" section at the end.
    
    Your task:
    1. Match every question with its exact corresponding solution.
    2. Fix any sentences that might be jumbled due to PDF column formatting.
    3. Return the output STRICTLY as a valid JSON array of objects. 
    
    The JSON must look exactly like this format:
    [
      {{"question": "What is the capital of France?", "solution": "Paris."}},
      {{"question": "Solve for x: 2x = 4", "solution": "x = 2."}}
    ]
    
    Do not include any markdown formatting like ```json or any other conversational text in your response. Just return the raw JSON array.
    
    RAW EXAM PAPER TEXT:
    {full_text}
    """
    
    try:
        # Send the prompt to the AI
        response = model.generate_content(prompt)
        
        # Read the AI's response and convert it from text into a Python list
        json_string = response.text.strip()
        
        # Sometimes the AI ignores rules and adds markdown anyway, so we clean it just in case
        if json_string.startswith("```json"):
            json_string = json_string[7:-3].strip()
            
        extracted_data = json.loads(json_string)
        return extracted_data
        
    except Exception as e:
        return [{"question": "AI Processing Error", "solution": f"The AI encountered an error: {e}"}]


# --- WEB APP INTERFACE ---

st.title("🤖 AI-Powered PDF Extractor")
st.write("Upload a PDF document. Our AI will read the text, fix any column issues, and perfectly match your questions and answers!")

uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

if uploaded_file is not None:
    st.info("Reading PDF and sending to AI... this usually takes 5-10 seconds.")
    
    try:
        # 1. Read the PDF text (we can use basic extraction now, because the AI is smart enough to fix the column jumble!)
        full_text = ""
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    full_text += extracted + "\n"
                    
        # 2. Pass the text to our AI function
        results = extract_qa_with_ai(full_text)
        
        # 3. Display the results
        if results and results[0]["question"] != "AI Processing Error":
            st.success(f"AI successfully extracted {len(results)} items!")
            
            for i, item in enumerate(results, 1):
                st.subheader(f"Item {i}")
                st.write(item["question"])
                
                st.markdown("**Solution:**")
                st.info(item["solution"]) 
                
                st.divider() 
                
        else:
            st.error(results[0]["solution"])
            
    except Exception as e:
        st.error(f"An error occurred while reading the PDF: {e}")
