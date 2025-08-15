import requests
import time
import os
import sys
from colorama import init, Fore, Style
from tabulate import tabulate
import smtplib
from email.message import EmailMessage

init(autoreset=True)

EMAIL_ADDRESS = "YOUR EMAIL"
EMAIL_PASSWORD = "YOUR GMAIL WEB AUTH PW"
TO_EMAIL = "WHERES IT GOING CAN ALSO BE SAME AS THE CURRENT"
SEEN_JOBS_FILE = "seen_jobs.txt"

GRAPHQL_URL = "https://qy64m4juabaffl7tjakii4gdoa.appsync-api.eu-west-1.amazonaws.com/graphql"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer Status|logged-in|Session|eyJhbGciOiJLTVMiLCJ0eXAiOiJKV1QifQ.eyJpYXQiOjE3NDg3OTc2MjgsImV4cCI6MTc0ODgwMTIyOH0.AQICAHh9Y3eh+eSawH7KZrCzIFETq1dycngugjOljT8N4eCxVgFLmzrkyr2N1poEGOR2Wpx8AAAAtDCBsQYJKoZIhvcNAQcGoIGjMIGgAgEAMIGaBgkqhkiG9w0BBwEwHgYJYIZIAWUDBAEuMBEEDLGo9NYf0IMdbT3tngIBEIBtFwYPf5AUELF7c+snuv8SR4iMnuzIXKsG3XtaJdkP0N74EQ+r8ZsySaDJQUrT17u6k+kxcTArmGJnFFSUEdvZdecUtglRoIuqhbE+8ztdawbBKY7yJBh6VPiJfk9yuwvfPzOWZKGbs7Zen1WhHQ==",
    "User-Agent": "Mozilla/5.0 ..."
}

GRAPHQL_PAYLOAD = {
    "operationName": "searchJobCardsByLocation",
    "variables": {
        "searchJobRequest": {
            "locale": "en-GB",
            "country": "United Kingdom",
            "keyWords": "",
            "equalFilters": [],
            "containFilters": [{"key": "isPrivateSchedule", "val": ["true", "false"]}],
            "rangeFilters": [],
            "orFilters": [],
            "dateFilters": [],
            "sorters": [{"fieldName": "totalPayRateMax", "ascending": "false"}],
            "pageSize": 100,
            "consolidateSchedule": True
        }
    },
    "query": """
        query searchJobCardsByLocation($searchJobRequest: SearchJobRequest!) {
          searchJobCardsByLocation(searchJobRequest: $searchJobRequest) {
            nextToken
            jobCards {
              jobId
              jobTitle
              city
              state
              locationName
              totalPayRateMin
              totalPayRateMax
              currencyCode
              employmentType
              jobType
              __typename
            }
            __typename
          }
        }
    """
}

def load_seen_jobs():
    if not os.path.exists(SEEN_JOBS_FILE):
        return set()
    with open(SEEN_JOBS_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f.readlines())

def save_seen_job(job_id):
    with open(SEEN_JOBS_FILE, "a", encoding="utf-8") as f:
        f.write(job_id + "\n")

def send_email(subject, body):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = TO_EMAIL
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        print(f"{Fore.YELLOW}[INFO] Email notification sent!{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Failed to send email: {e}{Style.RESET_ALL}")

def display_jobs(job_list):
    seen_jobs = load_seen_jobs()
    headers = ["Job Title", "Location", "Pay Rate", "Employment Type", "Job Type"]
    rows = []

    for job in job_list:
        job_id = job["jobId"]
        title = job["jobTitle"]
        location = job.get("locationName") or f"{job.get('city')}, {job.get('state')}"
        pay_min = job.get("totalPayRateMin")
        pay_max = job.get("totalPayRateMax")
        currency = job.get("currencyCode") or ""
        pay_str = f"{currency} {pay_min} - {pay_max}" if pay_min and pay_max else "N/A"
        emp_type = job.get("employmentType") or "N/A"
        job_type = job.get("jobType") or "N/A"

        job_info_str = f"{title} | {location} | {pay_str} | {emp_type} | {job_type}"

        if job_id not in seen_jobs:
            colored_row = [f"{Fore.GREEN}{title}{Style.RESET_ALL}",
                           f"{Fore.GREEN}{location}{Style.RESET_ALL}",
                           f"{Fore.GREEN}{pay_str}{Style.RESET_ALL}",
                           f"{Fore.GREEN}{emp_type}{Style.RESET_ALL}",
                           f"{Fore.GREEN}{job_type}{Style.RESET_ALL}"]
            rows.append(colored_row)

            subject = f"New Amazon Job Posted: {title}"
            body = (f"Job Title: {title}\nLocation: {location}\n"
                    f"Pay Rate: {pay_str}\nEmployment Type: {emp_type}\nJob Type: {job_type}\n\n"
                    f"Job ID: {job_id}")

            send_email(subject, body)
            save_seen_job(job_id)
        else:
            rows.append([title, location, pay_str, emp_type, job_type])

    print("\n" + tabulate(rows, headers=headers, tablefmt="fancy_grid"))
    print(f"\n[INFO] Total jobs fetched: {len(job_list)}")

def fetch_jobs_loop():
    while True:
        print("[INFO] Sending GraphQL request to fetch jobs...")
        try:
            response = requests.post(GRAPHQL_URL, json=GRAPHQL_PAYLOAD, headers=HEADERS)
            response.raise_for_status()
            data = response.json()
            jobs_data = data.get("data", {}).get("searchJobCardsByLocation", {}).get("jobCards", [])

            if not jobs_data:
                print("[WARNING] No jobs found in response.")
            else:
                print(f"[INFO] Found {len(jobs_data)} job cards.")
                display_jobs(jobs_data)

        except Exception as e:
            print(f"[ERROR] Failed to fetch jobs: {e}")

        print("[INFO] Waiting 60 seconds before next fetch...")
        time.sleep(60)

if __name__ == "__main__":
    fetch_jobs_loop()