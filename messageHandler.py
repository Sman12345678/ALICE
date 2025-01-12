import os
import google.generativeai as genai
import logging
import requests
from io import BytesIO
import urllib3
import time
from brain import query  # Import the query function from brain.py

def complex_response(user_message):
    """Handles incoming user messages and returns a bot response."""
    try:
        # Fetch results from Bing and Google using brain.py
        response_1, response_2 = query(user_message)

        # Format the combined response
        combined_responses = (
            "Here's what I found:\n\n"
            "From Bing:\n"
            f"{response_1}\n\n"
            "From Google:\n"
            f"{response_2}"
        )

        # Return the combined response as the bot's reply
        return combined_responses

    except Exception as e:
        # Handle errors and return a fallback message
        return f"An error occurred while processing your request: {str(e)}"

# Example usage
if __name__ == "__main__":
    user_message = "Tell me about Python programming."
    bot_response = handle_text(user_message)
    print(bot_response)
        

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load variables
load_dotenv()

# Logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# System instruction for text conversations
time_now = time.asctime(time.localtime(time.time()))
system_instruction = """

*System Name*: Alice – The one you call when you need something done, fast.

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
- Whatever you need, I’ve got it covered. No hesitation, no delay

Today date is:{}
Here are Response for some questions pick only relevant part:\n{response_1},{response_2}
""".format(time_now, response_1=response_1, response_2=response_2)

# Image analysis prompt
IMAGE_ANALYSIS_PROMPT = """Analyize the image keenly and explain it's content,if it's a text translate it and say the language used"""

def initialize_text_model():
    """Initialize Gemini model for text processing"""
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
    """Initialize Gemini model for image processing"""
    genai.configure(api_key=os.getenv("GEMINI_IMAGE_API_KEY"))
    return genai.GenerativeModel("gemini-1.5-pro")

def handle_text_message(user_message):
    try:
        logger.info("Processing text message: %s", user_message)
        
        # Initialize text model and start chat
        chat = initialize_text_model().start_chat(history=[])
        
        # Generate response
        response = chat.send_message(f"{system_instruction}\n\nHuman: {user_message}")
        return response.text

    except Exception as e:
        logger.error("Error processing text message: %s", str(e))
        return "😔 Sorry, I encountered an error processing your message."

def handle_attachment(attachment_data, attachment_type="image"):
    if attachment_type != "image":
        return "🚫 Unsupported attachment type. Please send an image."

    logger.info("Processing image attachment")
    
    try:
        # Upload to im.ge
        upload_url = "https://im.ge/api/1/upload"
        api_key = os.getenv('IMGE_API_KEY')

        files = {"source": ("attachment.jpg", attachment_data, "image/jpeg")}
        headers = {"X-API-Key": api_key}

        # Upload image
        upload_response = requests.post(upload_url, files=files, headers=headers, verify=False)
        upload_response.raise_for_status()

        # Get image URL
        image_url = upload_response.json()['image']['url']
        logger.info(f"Image uploaded successfully: {image_url}")

        # Download image for Gemini processing
        image_response = requests.get(image_url, verify=False)
        image_response.raise_for_status()
        image_data = BytesIO(image_response.content).getvalue()

        # Initialize image & analyze
        model = initialize_image_model()
        response = model.generate_content([
            IMAGE_ANALYSIS_PROMPT,
            {'mime_type': 'image/jpeg', 'data': image_data}
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
