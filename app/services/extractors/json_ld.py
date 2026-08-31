import json
from datetime import datetime
from bs4 import BeautifulSoup

from app.models.job import Job
from app.services.text_cleaner import clean_html
from app.services.job_enrichment import enrich_job_description


def extract_jobs_from_json_ld(html_content: str, url: str) -> list[Job]:
    """
    Extracts structured Job data from JSON-LD blocks within HTML content.
    Returns a list of normalized Job models.
    """
    if not html_content:
        return []

    # Parse the HTML to find hidden script tags
    soup = BeautifulSoup(html_content, "html.parser")
    json_ld_scripts = soup.find_all("script", type="application/ld+json")
    
    extracted_jobs = []

    for script in json_ld_scripts:
        if not script.string:
            continue
            
        try:
            data = json.loads(script.string)
        except json.JSONDecodeError:
            continue
            
        # JSON-LD can be a single dict or a list of dicts. Normalize to a list.
        if isinstance(data, dict):
            data = [data]
            
        for item in data:
            # We strictly want JobPosting schemas
            if item.get("@type") != "JobPosting":
                continue
                
            # --- 1. Identity ---
            title = item.get("title", "Unknown Title")
            
            # Safely extract company name
            hiring_org = item.get("hiringOrganization", {})
            company = hiring_org.get("name", "Unknown Company")
            
            # Generate a fallback ID if the identifier is missing
            identifier = item.get("identifier", {})
            job_id = str(identifier.get("value")) if isinstance(identifier, dict) else str(identifier)
            if not job_id or job_id == "None":
                job_id = f"{company}-{title}".replace(" ", "-").lower()

            # --- 2. Location --- 
            # Handling nested Schema.org Location objects
            location_name = ""
            job_location = item.get("jobLocation", {})
            if isinstance(job_location, dict):
                address = job_location.get("address", {})
                if isinstance(address, dict):
                    loc_parts = [
                        address.get("addressLocality"),
                        address.get("addressRegion"),
                        address.get("addressCountry")
                    ]
                    # Join available location parts (e.g., "Bengaluru, Karnataka, IN")
                    location_name = ", ".join(filter(None, loc_parts))

            # --- 3. Clean Description ---
            raw_description = item.get("description", "")
            enrichment = enrich_job_description(raw_description)

            # --- 4. Dates ---
            posted_at = None
            date_posted_str = item.get("datePosted")
            if date_posted_str:
                try:
                    # Simple ISO format parsing
                    posted_at = datetime.fromisoformat(date_posted_str.replace("Z", "+00:00"))
                except ValueError:
                    pass

            # --- 5. Map to the Job model ---
            job = Job(
                id=job_id,
                title=title,
                company=company,
                location=location_name,
                **{
                    "description": enrichment.description,
                    "experience_required": enrichment.experience_required,
                    "experience_years_required": enrichment.experience_years_required,
                    "required_skills": enrichment.required_skills or [],
                    "preferred_skills": enrichment.preferred_skills or [],
                    "description_status": enrichment.description_status,
                    "skills_status": enrichment.skills_status,
                    "experience_status": enrichment.experience_status,
                    "description_length": len(enrichment.description),
                },
                application_url=url,
                source_url=url,
                source="career_page_json_ld",
                posted_at=posted_at,
                fetched_at=datetime.utcnow()
            )
            extracted_jobs.append(job)

    return extracted_jobs
