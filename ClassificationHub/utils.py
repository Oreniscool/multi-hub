import pandas as pd
import os
import requests
import time

def load_data(file_or_demo):
    """
    Loads data from a CSV file object or generates demo data.
    """
    if file_or_demo == "demo":
        return pd.DataFrame({
            'email_id': range(1, 21),
            'email_content': [
                "Subject: CRITICAL: Production Server Down\nFrom: DevOps Team\nDear IT Department,\nOur main production server (srv-prod-01) is completely unresponsive. All customer transactions are failing. We need immediate attention as this is causing significant revenue loss. Please escalate to senior engineers immediately.",
                "Subject: Board Meeting Agenda - Tomorrow 9 AM\nFrom: CEO Office\nDear Executive Team,\nAttached is the finalized agenda for tomorrow's board meeting. Please review the Q4 financial projections and be prepared to discuss the strategic initiatives. Your presence is mandatory.",
                "Subject: Office Supplies Order\nFrom: Admin Department\nHi Team,\nWe're placing our monthly office supplies order next week. If you need anything (notebooks, pens, etc.), please reply to this email by Friday. No rush.",
                "Subject: URGENT: Data Breach Detected\nFrom: Security Team\nImmediate Action Required: We've detected unauthorized access to our customer database at 3:47 AM. All systems are being locked down. Please do not access any customer data until further notice. Emergency meeting at 10 AM.",
                "Subject: Welcome to the Team!\nFrom: HR Department\nDear New Hire,\nWelcome aboard! We're excited to have you join our team. Your onboarding session is scheduled for Monday at 10 AM. Please bring your ID and complete the attached forms at your convenience.",
                "Subject: Client Contract Expiring in 48 Hours\nFrom: Sales Manager\nDear Account Team,\nOur largest client's contract expires in 48 hours and we haven't received renewal confirmation. This represents 30% of our annual revenue. Please contact them immediately and escalate if needed.",
                "Subject: Team Building Event - Next Month\nFrom: HR Department\nHi Everyone,\nWe're planning a team building event for next month. We're considering bowling or an escape room. Please vote on your preference when you have a moment. Looking forward to it!",
                "Subject: Payment Overdue - Account Suspension Imminent\nFrom: Finance Department\nDear Client Services,\nAccount #45789 has an outstanding balance of $125,000 that is 60 days overdue. Per our contract terms, we must suspend their services tomorrow unless payment is received. Please follow up immediately.",
                "Subject: Weekly Newsletter - March Edition\nFrom: Marketing Team\nHello Team,\nCheck out this month's newsletter featuring employee spotlights, upcoming events, and interesting articles. Feel free to read it when you have some downtime. Enjoy!",
                "Subject: CEO Resignation Announcement\nFrom: Board of Directors\nDear All Staff,\nWe need to inform you that our CEO has submitted their resignation effective immediately due to personal reasons. An all-hands meeting will be held today at 4 PM to discuss the transition plan. Your attendance is required.",
                "Subject: Compliance Audit Failed - Corrective Actions Needed\nFrom: Compliance Officer\nDear Department Heads,\nOur annual compliance audit has revealed several critical violations that must be addressed within 7 days to avoid regulatory penalties. Please review the attached report and submit your corrective action plans by EOD tomorrow.",
                "Subject: Coffee Chat?\nFrom: Colleague\nHey,\nHaven't caught up with you in a while! Want to grab coffee sometime this week or next? No pressure, just thought it would be nice to chat. Let me know!",
                "Subject: Website Performance Degradation\nFrom: IT Monitoring\nDear Web Team,\nOur monitoring system shows the website response time has increased by 300% in the last hour. Customer complaints are coming in. Please investigate and resolve as this is affecting user experience.",
                "Subject: Quarterly Training Session\nFrom: Learning & Development\nDear Team Members,\nOur quarterly professional development training is scheduled for next month. Topics include leadership skills and project management. Please register by the end of this week if you're interested.",
                "Subject: IMMEDIATE: Legal Subpoena Received\nFrom: Legal Department\nDear Records Management,\nWe have received a court subpoena requiring all email communications and documents related to Project Phoenix. We must comply within 72 hours. Please halt all document destruction and preserve all related materials immediately.",
                "Subject: Conference Room Booking\nFrom: Admin\nHi,\nJust confirming I've booked Conference Room B for your meeting next Thursday at 2 PM. Let me know if you need any AV equipment setup. Thanks!",
                "Subject: Product Recall - Health & Safety Issue\nFrom: Quality Assurance\nIMMEDIATE ACTION: We've identified a safety defect in Product SKU-7821 that could cause injury. All units must be recalled immediately. Contact all customers who purchased this product in the last 6 months. Legal and PR teams are standing by.",
                "Subject: Congratulations on Your Work Anniversary\nFrom: HR Department\nDear Team Member,\nCongratulations on completing 5 years with our company! We appreciate your dedication and contributions. A small celebration is planned for next week. Details to follow.",
                "Subject: Investor Meeting Rescheduled\nFrom: CFO Office\nDear Leadership Team,\nThe investor presentation scheduled for Friday has been moved to Monday at 2 PM due to scheduling conflicts. Please ensure your financial projections are updated. This meeting is critical for our Series B funding.",
                "Subject: Lunch Menu Update\nFrom: Cafeteria Services\nHello Everyone,\nWe've updated our cafeteria menu with some new healthy options based on your feedback. Check out the salad bar and new smoothie selections. Hope you enjoy them!"
            ]
        })
    else:
        try:
            return pd.read_csv(file_or_demo)
        except Exception as e:
            return None

def _hf_config():
    token = os.getenv("HF_API_TOKEN", "").strip() or os.getenv("HUGGINGFACEHUB_API_TOKEN", "").strip()
    model_id = os.getenv("HF_MODEL_ID", "mistralai/Mistral-7B-Instruct-v0.3").strip()
    api_url = os.getenv("HF_API_URL", f"https://router.huggingface.co/hf-inference/models/{model_id}").strip()
    return token, api_url


def _generate_with_mistral(prompt: str) -> str:
    token, api_url = _hf_config()
    if not token:
        raise ValueError("HF_API_TOKEN is not configured in environment.")

    response = requests.post(
        api_url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "inputs": prompt,
            "parameters": {"max_new_tokens": 100, "temperature": 0.1, "return_full_text": False},
            "options": {"wait_for_model": True},
        },
        timeout=120,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"HF inference failed ({response.status_code}): {response.text}")

    data = response.json()
    if isinstance(data, list) and data and isinstance(data[0], dict):
        text = (data[0].get("generated_text") or "").strip()
        if text:
            return text
    raise RuntimeError("HF response did not include generated_text.")


def classify_text(text, prompt_template):
    """
    Classifies a single text string using Mistral via Hugging Face.
    """
    try:
        prompt = (
            f"{prompt_template}\n\n"
            f"Text: {text}\n\n"
            "Return only the final category label as plain text."
        )
        return _generate_with_mistral(prompt).splitlines()[0].strip()
    except Exception as e:
        return f"Error: {str(e)}"

def classify_batch(df, column, prompt_template, progress_bar=None):
    """
    Classifies a batch of texts from a DataFrame.
    """
    results = []
    total = len(df)
    
    for i, text in enumerate(df[column]):
        category = classify_text(text, prompt_template)
        results.append(category)
        
        if progress_bar:
            progress_bar.progress((i + 1) / total)
            
        # Basic rate limiting handling
        time.sleep(0.5) 
        
    return results
