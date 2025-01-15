import requests
from bs4 import BeautifulSoup
import os

def scrape_bing(user_message):
    """Scrapes Bing search results using the specified <div> class."""
    search_url = f"https://bing.com/search?q={user_message}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extract search results using the specific <div> class
        results = []
        for div in soup.find_all('div', class_="rwrl rwrl_sec rwrl_padref rwrl_fontexp rwrl_bchl")[:5]:  # Limit to top 5
            title_tag = div.find('h2')
            link_tag = div.find('a')
            snippet_tag = div.find('p')
            
            if title_tag and link_tag:
                title = title_tag.get_text(strip=True)
                link = link_tag['href']
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else "No description available."
                results.append(f"Title: {title}\nLink: {link}\nSnippet: {snippet}\n")
        
        return "\n".join(results) if results else "No results found on Bing."
    except Exception as e:
        return f"Error scraping Bing: {str(e)}"

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
