import requests
from bs4 import BeautifulSoup
import os
import urllib3

url="https://bing.com/search?q={message}"
"""
I disabled ssl certificate check, be careful bro
But with it disabled we can scrap many sites.
"""

# Disable annoying warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def scrape_bing(user_message):
    url="https://bing.com/search?q={user_message}"
    try:
        # SSL verification disabled✌️
        response = requests.get(url, verify=False)  
        response.raise_for_status()  
        
        # Parse the content
        soup = BeautifulSoup(response.content, 'html.parser')
        results = soup.get_text(separator='\n', strip=True)  # Extract the text
        
        return results 
    except requests.exceptions.RequestException as e:
        # W check errors. 
        return f"An error bro: {e}"

def google_search(user_message):
    """Fetches results from Google Search API using a direct URL request."""
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        cse_id = os.getenv("GOOGLE_CSE_ID")
        
        # Construct the API URL
        search_url = (
            f"https://www.googleapis.com/customsearch/v1"
            f"?key={api_key}&cx={cse_id}&q={user_message}&num=5"
        )
        
        response = requests.get(search_url)
        response.raise_for_status()
        result = response.json()
        
        # Extract search results
        results = []
        for item in result.get('items', []):
            title = item['title']
            link = item['link']
            snippet = item.get('snippet', 'No description available.')
            results.append(f"Title: {title}\nLink: {link}\nSnippet: {snippet}\n")
        
        return "\n".join(results) if results else "No results found on Google."
    except Exception as e:
        return f"Error with Google Search API: {str(e)}"

def query(user_message):
    """Fetches and returns search results from Bing and Google."""
    response_1 = scrape_bing(user_message)
    response_2 = google_search(user_message)
    return response_1, response_2
