
import requests
from bs4 import BeautifulSoup

url = "https://annas-archive.org/search?q="

def search(query: str):
    """Search Anna's Archive and return md5 links from results."""
    response = requests.get(url + query)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, 'html.parser')

    # Find all links to md5 pages
    md5_links = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        if '/md5/' in href:
            # Make it absolute if it's relative
            if href.startswith('/'):
                href = 'https://annas-archive.org' + href
            md5_links.append(href)

    return md5_links


if __name__ == "__main__":
    # Example usage
    import sys
    if len(sys.argv) > 1:
        query = ' '.join(sys.argv[1:])
        results = search(query)
        print(f"Found {len(results)} results:")
        for link in results:
            print(link)
    else:
        print("Usage: python search.py <query>")
