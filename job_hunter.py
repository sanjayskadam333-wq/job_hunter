import os
import json
import smtplib
from email.mime.text import MIMEText
import requests
import google.generativeai as genai

# Secrets from GitHub Environment
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
MY_RESUME = os.environ.get("MY_RESUME", "Your resume text here")

genai.configure(api_key=GEMINI_API_KEY)

# 1. Fetch Job Openings
def fetch_jobs():
    url = "https://remotive.com/api/remote-jobs?limit=10"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        jobs = []
        for item in data.get("jobs", [])[:5]:
            jobs.append({
                "title": item.get("title"),
                "company": item.get("company_name"),
                "url": item.get("url"),
                "description": item.get("description", "")[:2000]  # Truncated for token efficiency
            })
        return jobs
    except Exception as e:
        print(f"Error fetching jobs: {e}")
        return []

# 2. Score Match & Generate Cover Letter via Gemini AI
def evaluate_job(job):
    model = genai.GenerativeModel('gemini-3.8-flash')
    
    prompt = f"""
    You are an executive career coach AI. Evaluate this job opening against the candidate's resume.

    CANDIDATE RESUME:
    {MY_RESUME}

    JOB TITLE: {job['title']}
    COMPANY: {job['company']}
    JOB DESCRIPTION:
    {job['description']}

    Return ONLY a valid JSON object matching this structure:
    {{
        "match_score": 85,
        "is_qualified": true,
        "summary": "1-sentence summary of why this candidate is a strong fit.",
        "cover_letter": "A compelling 3-paragraph tailored cover letter."
    }}
    Mark "is_qualified" as true ONLY if match_score is >= 75.
    """
    
    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Evaluation error for {job['title']}: {e}")
        return None

# 3. Send Email Alert via Gmail SMTP
def send_email_alert(job, eval_data):
    subject = f"🎯 Job Match ({eval_data['match_score']}%): {job['title']} at {job['company']}"
    
    body = (
        f"🎯 NEW QUALIFIED JOB MATCH ({eval_data['match_score']}%)\n"
        f"=========================================\n\n"
        f"💼 Role: {job['title']}\n"
        f"🏢 Company: {job['company']}\n"
        f"🔗 Apply Here: {job['url']}\n\n"
        f"📝 AI Match Summary:\n{eval_data['summary']}\n\n"
        f"-----------------------------------------\n"
        f"📄 TAILORED COVER LETTER DRAFT:\n"
        f"-----------------------------------------\n\n"
        f"{eval_data['cover_letter']}\n"
    )
    
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = GMAIL_USER
    msg['To'] = GMAIL_USER

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        print(f"-> Email sent successfully for {job['title']}!")
    except Exception as e:
        print(f"Failed to send email: {e}")

# Execution Flow
if __name__ == "__main__":
    print("Fetching daily job openings...")
    jobs = fetch_jobs()
    
    for job in jobs:
        print(f"Analyzing: {job['title']} at {job['company']}...")
        eval_data = evaluate_job(job)
        
        if eval_data and eval_data.get("is_qualified"):
            send_email_alert(job, eval_data)
        else:
            print("-> Skipped (below 75% match threshold).")
