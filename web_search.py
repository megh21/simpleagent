import aiohttp
import asyncio
from bs4 import BeautifulSoup
import urllib.parse
from typing import List, Dict, Optional, Any

async def search_duckduckgo(query: str, num_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search the web using DuckDuckGo (no API key required)
    """
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
    }
    
    results = []
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                
                # Extract search results
                search_results = soup.find_all("div", class_="result")
                
                for i, result in enumerate(search_results):
                    if i >= num_results:
                        break
                    
                    title_element = result.find("a", class_="result__a")
                    snippet_element = result.find("a", class_="result__snippet")
                    
                    if title_element and snippet_element:
                        title = title_element.get_text().strip()
                        snippet = snippet_element.get_text().strip()
                        link = title_element.get("href")
                        
                        # Clean the URL from DuckDuckGo's redirect
                        if link and link.startswith("/l/?"):
                            parsed_url = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
                            if "uddg" in parsed_url:
                                link = parsed_url["uddg"][0]
                        
                        results.append({
                            "title": title,
                            "snippet": snippet,
                            "link": link,
                            "source": "web"
                        })
            
    return results

async def fetch_webpage_content(url: str) -> Optional[str]:
    """
    Fetch and extract the main content from a webpage
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")
                    
                    # Remove script and style elements
                    for script in soup(["script", "style"]):
                        script.decompose()
                    
                    # Get text content
                    text = soup.get_text(separator=' ', strip=True)
                    
                    # Clean up text (remove excessive whitespace)
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    text = '\n'.join(chunk for chunk in chunks if chunk)
                    
                    return text[:10000]  # Limit content size
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        
    return None