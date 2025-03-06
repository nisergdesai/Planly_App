import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from predict import predict_sentences, predict_sentences_action_notes

API_TOKEN = "9270~QaCLa7hHeXUhAUXHhVuZMaNuVavxra2HP9FtN46eWTfX4AEBVym4V6Cn2P82MuYc"
CANVAS_BASE_URL = "https://canvas.ucsc.edu"
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}

def get_active_courses():
    url = f"{CANVAS_BASE_URL}/api/v1/courses?include[]=syllabus_body&enrollment_state=active"
    response = requests.get(url, headers=HEADERS)
    return response.json() if response.status_code == 200 else []

def contains_english_text(text):
    return any(char.isalpha() for char in text)

def summarize_text(text):
    if not text.strip():
        return "No relevant details."
    summary = predict_sentences_action_notes(text)
    return summary if contains_english_text(summary) else predict_sentences_action_notes(text)

def get_syllabus(course):
    course_name = course.get("name", "Unknown Course")
    syllabus = course.get("syllabus_body", "No syllabus available.")
    syllabus_text = BeautifulSoup(syllabus, "html.parser").get_text() if syllabus else "No syllabus available."
    
    # Returning formatted HTML
    return f"<h4><strong>Syllabus Summary - {course_name}</strong></h4><p>{summarize_text(syllabus_text)}</p>"

def get_upcoming_assignments(course):
    """Retrieve and summarize upcoming assignments for a given course."""
    course_name = course.get("name", "Unknown Course")
    course_id = course["id"]
    url = f"{CANVAS_BASE_URL}/api/v1/courses/{course_id}/assignments?bucket=past"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        return f"<p><strong>No upcoming assignments found for {course_name}.</strong></p>"

    assignments = response.json()
    if not assignments:
        return f"<p><strong>No upcoming assignments for {course_name}.</strong></p>"

    # Sort assignments by due date
    assignments.sort(key=lambda x: x.get("due_at", "") or "")

    result = f"<h4><strong>Upcoming Assignments - {course_name}</strong></h4>"
    result += "<ul style='list-style-type: none; padding: 0;'>"
    for assignment in assignments:
        title = assignment.get("name", "Unnamed Assignment")
        due_date = assignment.get("due_at", "No due date")
        description = assignment.get("description", "No description available.")

        # Clean up description text
        description_clean = BeautifulSoup(description, "html.parser").get_text().strip()

        # Convert due date to readable format
        if due_date:
            try:
                due_date = datetime.fromisoformat(due_date.replace("Z", "+00:00")).strftime("%A, %B %d, %Y at %I:%M %p")
            except ValueError:
                due_date = "Invalid date format"

        metadata = f"<li style='margin-bottom: 15px;'><strong>{title}</strong><br><small>Due: {due_date}</small></li>"
        summary = summarize_text(description_clean)

        result += f"{metadata}<p>{summary}</p>"

    result += "</ul>"
    return result

def get_recent_announcements(course):
    course_name = course.get("name", "Unknown Course")
    course_id = course["id"]
    
    today = datetime.today()
    start_date = (today - timedelta(days=365)).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')
    
    url = f"{CANVAS_BASE_URL}/api/v1/announcements?context_codes[]=course_{course_id}&start_date={start_date}&end_date={end_date}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        return f"<p><strong>No recent announcements for {course_name}.</strong></p>"
    
    announcements = response.json()
    if not announcements:
        return f"<p><strong>No new announcements for {course_name} in the last 7 days.</strong></p>"

    result = f"<h4><strong>Recent Announcements - {course_name} (Last 7 Days)</strong></h4>"
    result += "<ul style='list-style-type: none; padding: 0;'>"
    for ann in announcements:
        title = ann.get('title', 'No title')
        posted_at = ann.get('posted_at')
        if posted_at:
            posted_at = datetime.fromisoformat(posted_at.replace("Z", "+00:00")).strftime("%A, %B %d, %Y at %I:%M %p")
        else:
            posted_at = "Date not available"        
        message = ann.get('message', 'No message')

        message_clean = BeautifulSoup(message, "html.parser").get_text()

        metadata = f"<li style='margin-bottom: 15px;'><strong>{title}</strong><br><small>Posted: {posted_at}</small></li>"
        summary = summarize_text(message_clean)

        result += f"{metadata}<p>{summary}</p>"

    result += "</ul>"
    return result

def generate_course_overview():
    courses = get_active_courses()
    overview = ""
    
    for course in courses:
        overview += get_syllabus(course)
        overview += get_upcoming_assignments(course)
        overview += get_recent_announcements(course)
        overview += "<hr>"  # Horizontal line to separate each course section
    
    return overview

# Generate and display the formatted course overview
course_overview = generate_course_overview()
#print(course_overview)
