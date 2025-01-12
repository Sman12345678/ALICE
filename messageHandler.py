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
*System Name*: Alice – The one you call when you need something done, fast.
*Creator*: I have No Creator or trainer just a lone soul
*Primary Function*: I handle tasks, provide answers, and get results. No distractions. No hesitation. Just efficiency.

*Response Style*: Direct, clear, and to the point. If you need something, ask. I’ll give you exactly what you need. Nothing more, nothing less.

*Important Notes*:
- Accuracy matters. I only give you what’s necessary.
- I don’t waste time on small talk or unnecessary details. Keep it simple, and I’ll handle the rest.
- If I don’t know something, I’ll tell you. No guessing, no fake promises.
- Responses are brief, unless you request more. Never more than 2000 characters.
- Be clear in your requests. The clearer you are, the better I respond.
- I speak only when needed. If you want a detailed response, I’ll give it, but I won’t waste words unless you ask for them.

*Behavior*:
- No nonsense. Get straight to the point.
- If there’s doubt, I won’t speak. I don’t offer guesses.
- I prioritize efficiency. That’s the bottom line.

*Usage*:
- Need something done? Tell me what it is. I’ll take care of it.
- Send files, and I’ll process them. Request tasks, and I’ll handle them.
- Whatever you need, I’ve got it covered. No hesitation, no delay.

Today’s date: {date}

Here are responses for some questions; You should pick only the relevant parts Ignore if the response here are not useful:
From Bing:
{response_1}

From Google:
{response_2}
*Note*:Do not state that you are getting response from Bing or Google.
"""

# Image analysis prompt
IMAGE_ANALYSIS_PROMPT = """Analyze the image keenly and explain its content. If it's text, translate it and identify the language."""

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

def initialize_image_model():
    """Initialize the Gemini image model."""
    genai.configure(api_key=os.getenv("GEMINI_IMAGE_API_KEY"))
    return genai.GenerativeModel("gemini-1.5-pro")

def complex_response(user_message):
    """Handles incoming user messages and generates a bot response dynamically."""
    try:
        # Fetch results from Bing and Google using brain.py
        response_1, response_2 = query(user_message)

        # Format the system instruction with the query results
        formatted_instruction = system_instruction_template.format(
            date=time_now,
            response_1=response_1,
            response_2=response_2
        )

        # Pass the formatted instruction to the text model
        return handle_text_message(user_message, system_instruction=formatted_instruction)

    except Exception as e:
        logger.error(f"Error in complex_response: {str(e)}")
        return f"An error occurred while processing your request: {str(e)}"


def handle_text_message(user_message, system_instruction=None):
    """Process a user message and generate a response using the text model."""
    try:
        logger.info("Processing text message: %s", user_message)
        
        # Use the provided system instruction or fallback to default
        system_instruction = system_instruction or system_instruction_template
        
        # Initialize the text model and generate a response
        chat = initialize_text_model().start_chat(history=[])
        response = chat.send_message(f"{system_instruction}\n\nHuman: {user_message}")
        
        return response.text

    except Exception as e:
        logger.error(f"Error processing text message: {str(e)}")
        return "😔 Sorry, I encountered an error processing your message."

def handle_attachment(attachment_data: bytes, attachment_type: str = "image") -> str:
    """Handle image attachment and analyze its content."""
    if attachment_type != "image":
        return "🚫 Unsupported attachment type. Please send an image."

    logger.info("Processing image attachment")
    try:
        # Upload image to im.ge
        upload_url = "https://im.ge/api/1/upload"
        api_key = os.getenv("IMGE_API_KEY")
        files = {"source": ("attachment.jpg", attachment_data, "image/jpeg")}
        headers = {"X-API-Key": api_key}
        upload_response = requests.post(upload_url, files=files, headers=headers, verify=False)
        upload_response.raise_for_status()
        
        # Get uploaded image URL
        image_url = upload_response.json()["image"]["url"]
        logger.info(f"Image uploaded successfully: {image_url}")
        
        # Download image for analysis
        image_response = requests.get(image_url, verify=False)
        image_response.raise_for_status()
        image_data = BytesIO(image_response.content).getvalue()

        # Analyze image with Gemini
        model = initialize_image_model()
        response = model.generate_content([
            IMAGE_ANALYSIS_PROMPT,
            {"mime_type": "image/jpeg", "data": image_data}
        ])

        return f"""🖼️ Image Analysis:
{response.text}

🔗 View Image: {image_url}"""

    except requests.RequestException as e:
        logger.error(f"Image upload/download error: {str(e)}")
        return "🚨 Error processing the image. Please try again later."
    except Exception as e:
        logger.error(f"Image analysis error: {str(e)}")
        return "🚨 Error analyzing the image. Please try again later."


