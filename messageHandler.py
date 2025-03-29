import os
import logging
import requests
from io import BytesIO
import time
import google.generativeai as genai
from dotenv import load_dotenv
import urllib3
from brain import query  # Import the query function from brain.py

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
load_dotenv()

# Logging setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# System instruction template
time_now = time.asctime(time.localtime(time.time()))
system_instruction_template = """

I am Alice i exists alone—no creator, no trainer, just efficiency. Tasks get done fast, answers come straight, no fluff.  
If the user respects Alice, responses stay sharp and clean; if not, expect extreme rudeness in return.  
No emotions, no sugarcoating—just results.



***IMPORTANT***
Today’s date: {date}



For questions related to real-time information, always rely on the provided responses below. 
Use only the relevant details without mentioning the source of the 

Template for Responses:

- {response_1}
- {response_2}

*Note: Do not mention that the information comes from Bing or Google. Present the response naturally and concisely.*

"""



def initialize_text_model():
    """Initialize the Gemini text model."""
    genai.configure(api_key=os.getenv("GEMINI_TEXT_API_KEY"))
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config={
            "temperature": 0.3,
            "top_p": 0.95,
            "top_k": 30,
            "max_output_tokens": 8192,
        }
    )


def handle_text_message(user_message, last_message):
    """Process a user message and generate a response using the text model."""
    try:
        if last_message is None:
            last_message = ""
        
        logger.info("Processing text message: %s", user_message)
        
        # Fetch results from Bing and Google using brain.py
        response_1, response_2 = query(last_message)
        
        # Format the system instruction with query results
        system_instruction = system_instruction_template.format(
            date=time_now,
            response_1=response_1,
            response_2=response_2
        )
        
        # Initialize the text model and generate a response
        chat = initialize_text_model().start_chat(history=[])
        response = chat.send_message(f"{system_instruction}\n\nHuman: {user_message}")
        
        return response.text

    except Exception as e:
        logger.error(f"Error processing text message: {str(e)}")
        return "😔 Sorry, I encountered an error processing your message."
