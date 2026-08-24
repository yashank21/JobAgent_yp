from app.services.http_client import HTTPClient
from bs4 import BeautifulSoup

def inspect_page(name, url):
    client = HTTPClient()
    print(f"--- Inspecting {name} ({url}) ---")
    try:
        response = client.get(url)
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        
        # Check for Next.js embedded data state
        next_data = soup.find("script", id="__NEXT_DATA__")
        if next_data:
            print(f"[{name}] Found __NEXT_DATA__ script payload!")
        
        # Check for any script containing job-like keywords
        scripts = soup.find_all("script")
        job_script_count = sum(1 for s in scripts if s.string and ("job" in s.string.lower() or "position" in s.string.lower()))
        print(f"[{name}] Total script tags: {len(scripts)}, Scripts mentioning 'job'/'position': {job_script_count}")
        
    except Exception as e:
        print(f"[{name}] Error: {e}")
    print("-" * 40)

if __name__ == "__main__":
    inspect_page("Razorpay", "https://razorpay.com/jobs/")
    inspect_page("Swiggy", "https://careers.swiggy.com/")
    inspect_page("Flipkart", "https://www.flipkartcareers.com/")