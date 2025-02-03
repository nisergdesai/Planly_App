import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# 🔹 Replace these with your actual details
API_TOKEN = "9270~QaCLa7hHeXUhAUXHhVuZMaNuVavxra2HP9FtN46eWTfX4AEBVym4V6Cn2P82MuYc"
CANVAS_BASE_URL = "https://canvas.ucsc.edu"

# 🔹 Authorization headers
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}

def get_courses():
    """Fetch all courses for the user."""
    url = f"{CANVAS_BASE_URL}/api/v1/courses"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        return response.json()
    else:
        print("❌ Error fetching courses:", response.text)
        return []

# 🔹 Example usage
courses = get_courses()

def get_assignments(course_id):
    """Fetch assignments for a given course ID."""
    url = f"{CANVAS_BASE_URL}/api/v1/courses/{course_id}/assignments"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Error fetching assignments for Course {course_id}:", response.text)
        return []

# 🔹 Example usage (fetch assignments for the first course)
'''if courses:
    for course in courses:
        first_course_id = course["id"]
        assignments = get_assignments(first_course_id)

        print(f"\n📌 Assignments for {course['name']}:")
        for assignment in assignments:
            print(f"- {assignment['name']} (Due: {assignment['due_at']})")'''

def get_announcements(course_id):
    """Fetch announcements for a given course ID from the last 4 years."""
    # Calculate the date range (4 years ago to today)
    today = datetime.today()
    start_date = today - timedelta(days=4 * 365)  # Approximation, consider leap years if needed
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = today.strftime('%Y-%m-%d')

    # Construct the URL with dynamic date range
    url = f"{CANVAS_BASE_URL}/api/v1/announcements?context_codes[]=course_{course_id}&start_date={start_date_str}&end_date={end_date_str}"

    # Make the request
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        announcements = response.json()
        if announcements:
            return announcements
        else:
            print(f"No announcements found for Course {course_id} in the last 4 years.")
    else:
        print(f"❌ Error fetching announcements for Course {course_id}: {response.text}")
    return []

"""Display announcements for the first course in the courses list."""
if courses:
    first_course_id = courses[0]["id"]
    announcements = get_announcements(first_course_id)

    if announcements:
        print(f"\n📢 Announcements for {courses[0]['name']}:")
        for ann in announcements:
            # Clean up HTML tags if any (using BeautifulSoup)
            message_clean = BeautifulSoup(ann['message'], "html.parser").get_text()

            # Display the relevant details
            print(f"- Title: {ann['title']}")
            print(f"  Posted at: {ann['posted_at']}")
            print(f"  Message: {message_clean}\n")  
    else:
        print(f"No announcements found for Course {courses[0]['name']}.")







