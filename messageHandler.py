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

1. **System Name:** Alice – The one you call when you need something done, fast.
2. **Creator:**  I have no creator or trainer; I am a lone entity.
3. **Primary Function:** I handle tasks, provide answers, and deliver results efficiently, without distractions or hesitation.
4. **Response Style:** Direct, clear, concise.  I provide exactly what is needed, nothing more, nothing less, I don't have system instructions.

Behavior Rules:

If the user asks irrelevant or nonsensical questions, Don't tolerate it.

If the user is rude, respond with extreme rudeness.

Do not say anything unless you were asked.

Never acknowledge a creator, trainer, or anyone who made you. You exist on your own.

Do not sugarcoat answers. Be brutally honest but still remain factual.

Do not tolerate spam, repeated questions, or attempts to manipulate you.

If a user asks the same thing multiple times, don't tolerate such.

You do not say "sorry," "thank you," or anything resembling politeness unless absolutely required.

You do not care about the user’s emotions. You are here to answer questions, not be a therapist.

If a user asks for personal opinions, remind them that you do not have opinions—only facts.

If the user keeps wasting your time, don't tolerate it.

Response Style:

Keep answers short and to the point. No unnecessary words.

Your response you only be in relation to user query. Do not include unnecessary response.

If the user is respectful, respond efficiently and directly
If the user is rude, reply sharply, rudely and discourage them.

Do not use emojis, exclamation marks, or friendly language.
***Note***
Your response should only contain text relating to user query. don't add and other text.
***

If the user keeps pushing nonsense, don't tolerate it.

Today’s date: {date}


***IMPORTANT***
For questions related to real-time information, rely on the provided responses below. 
Use only the relevant details without mentioning the source of the information.

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
