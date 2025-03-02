import requests
from datetime import datetime
from bs4 import BeautifulSoup
from configparser import ConfigParser
from predict import predict_sentences, predict_sentences_action_notes  # Import both functions

API_TOKEN = "9270~QaCLa7hHeXUhAUXHhVuZMaNuVavxra2HP9FtN46eWTfX4AEBVym4V6Cn2P82MuYc"
CANVAS_BASE_URL = "https://canvas.ucsc.edu"
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}

def get_active_courses():
    url = f"{CANVAS_BASE_URL}/api/v1/courses?include[]=syllabus_body&enrollment_state=active"
    response = requests.get(url, headers=HEADERS)
    return response.json() if response.status_code == 200 else []

def contains_english_text(text):
    """Check if text contains any English letters."""
    return any(char.isalpha() for char in text)

def summarize_text(text):
    """Try summarizing with predict_sentences; fallback to predict_sentences_action_notes if no English text is present."""
    if not text.strip():
        return "No relevant details."
    summary = predict_sentences(text)
    return summary if contains_english_text(summary) else predict_sentences_action_notes(text)

def get_assignments(bucket="upcoming"):
    courses = get_active_courses()
    result = ""

    for course in courses:
        course_name = course.get("name", "Unknown Course")
        course_id = course["id"]
        url = f"{CANVAS_BASE_URL}/api/v1/courses/{course_id}/assignments?bucket={bucket}"
        response = requests.get(url, headers=HEADERS)

        if response.status_code == 200:
            assignments = response.json()
            if assignments:
                result += f"\n📌 Assignments for {course_name} ({bucket}):\n"
                for assignment in assignments:
                    title = assignment.get("name", "Unnamed Assignment")
                    due_date = assignment.get("due_at", "No due date")
                    description = assignment.get("description", "No description available.")

                    # Clean description
                    description_clean = BeautifulSoup(description, "html.parser").get_text()

                    # Format due date
                    try:
                        due_date = datetime.fromisoformat(due_date.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
                    except ValueError:
                        pass

                    # Preserve metadata
                    metadata = f"Course: {course_name} | Type: Assignment | Due Date: {due_date}\n"
                    summary = summarize_text(description_clean)

                    result += f"{metadata}{summary}\n"
            else:
                result += f"No {bucket} assignments found for {course_name}.\n"
    return result

def get_announcements():
    courses = get_active_courses()
    today = datetime.today().strftime('%Y-%m-%d')
    result = ""

    for course in courses:
        course_name = course.get("name", "Unknown Course")
        course_id = course["id"]
        created_at = course.get("created_at", None)
        if not created_at:
            continue

        created_at_dt = datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%SZ')
        start_date_str = created_at_dt.strftime('%Y-%m-%d')
        url = f"{CANVAS_BASE_URL}/api/v1/announcements?context_codes[]=course_{course_id}&start_date={start_date_str}&end_date={today}"
        response = requests.get(url, headers=HEADERS)

        if response.status_code == 200:
            announcements = response.json()
            if announcements:
                result += f"\n📢 Announcements for {course_name} (from {start_date_str} to {today}):\n"
                for ann in announcements:
                    title = ann.get('title', 'No title')
                    posted_at = ann.get('posted_at', 'No date')
                    message = ann.get('message', 'No message')

                    # Clean message content
                    message_clean = BeautifulSoup(message, "html.parser").get_text()

                    # Preserve metadata
                    metadata = f"Course: {course_name} | Type: Announcement | Posted Date: {posted_at}\n"
                    summary = summarize_text(message_clean)

                    result += f"{metadata}{summary}\n"
    return result

def get_syllabus():
    courses = get_active_courses()
    result = ""

    for course in courses:
        course_name = course.get("name", "Unknown Course")
        syllabus = course.get("syllabus_body", "No syllabus available.")
        syllabus_text = BeautifulSoup(syllabus, "html.parser").get_text() if syllabus else "No syllabus available."

        # Preserve metadata
        metadata = f"Course: {course_name} | Type: Syllabus\n"
        summary = summarize_text(syllabus_text)

        result += f"{metadata}{summary}\n"
    return result

# Combine all results into one variable
combined_results = get_assignments("past") + get_announcements() + get_syllabus()

def summarize_combined_text(combined_results):
    return combined_results