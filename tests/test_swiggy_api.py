from app.services.http_client import HTTPClient

def test_swiggy():
    client = HTTPClient()
    url = "https://swiggy.mynextshire.com/employer/careers/reqlist/get"
    
    print(f"Fetching jobs directly from Swiggy's API: {url}")
    try:
        # Many corporate APIs require standard headers or a POST/GET request
        response = client.get(url)
        print(f"Status Code: {response.status_code}")
        data = response.json()
        
        # Let's see how many jobs came back
        jobs_list = data.get("reqDetailsBOList", [])
        print(f"Successfully fetched {len(jobs_list)} jobs from Swiggy API!")
        
        if jobs_list:
            sample = jobs_list[0]
            print(f"Sample Job: {sample.get('title', sample.get('reqTitle'))}")
            
    except Exception as e:
        print(f"Error calling Swiggy API: {e}")

if __name__ == "__main__":
    test_swiggy()