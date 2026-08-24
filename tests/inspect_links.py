from app.services.http_client import HTTPClient
from bs4 import BeautifulSoup
import re

def inspect_links_and_apis(name, url):
    client = HTTPClient()
    print(f"--- Checking Network/Scripts for {name} ---")
    try:
        response = client.get(url)
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        
        # Look for script sources or api paths
        for script in soup.find_all("script", src=True):
            src = script["src"]
            if any(keyword in src.lower() for keyword in ["job", "career", "api", "workday", "greenhouse", "lever", "ashby", "graphql"]):
                print(f"  [Script API/ATS hint]: {src}")
                
        # Look for any inline text containing api or endpoints
        text_content = soup.get_text()
        matches = re.findall(r'https?://[^\s<>"]+api[^\s<>"]*', text_content, re.IGNORECASE)
        for m in set(matches):
            print(f"  [Found Endpoint URL]: {m}")

    except Exception as e:
        print(f"  [Error]: {e}")
    print("-" * 40)

if __name__ == "__main__":
    inspect_links_and_apis("Razorpay", "https://razorpay.com/jobs/")
    inspect_links_and_apis("Swiggy", "https://careers.swiggy.com/")
    inspect_links_and_apis("Flipkart", "https://www.flipkartcareers.com/")