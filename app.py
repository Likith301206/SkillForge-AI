from flask import Flask, render_template, request, redirect, url_for, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from tempfile import NamedTemporaryFile
import sqlite3
from flask import request
import os
import os
from werkzeug.utils import secure_filename
from flask import request
import fitz
import fitz
import easyocr
from PIL import Image
import io
import numpy as np
import google.generativeai as genai
from dotenv import load_dotenv
from career_data import career_data
app = Flask(__name__)
load_dotenv()

genai.configure(
    api_key=os.getenv("GEMINI_API_KEY")
)
model = genai.GenerativeModel("gemini-2.5-flash")
UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.secret_key = "skillforge_secret_key"
os.makedirs("database", exist_ok=True)
connection = sqlite3.connect("database/skillforge.db", check_same_thread=False)

cursor = connection.cursor()

# Users Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fullname TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL
)
""")

connection.commit()

# Profile Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS profile(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT,
    email TEXT UNIQUE,
    phone TEXT,
    college TEXT,
    department TEXT,
    semester TEXT,
    location TEXT,
    github TEXT,
    linkedin TEXT,
    portfolio TEXT,
    bio TEXT,
    profile_image TEXT
)
""")

connection.commit()

# Skills Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS skills(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_name TEXT NOT NULL,
    category TEXT NOT NULL,
    level TEXT NOT NULL,
    progress INTEGER,
    user_email TEXT NOT NULL
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS projects(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_name TEXT NOT NULL,
    tech_stack TEXT NOT NULL,
    description TEXT NOT NULL,
    github_link TEXT,
    live_link TEXT,
    status TEXT,
    progress INTEGER,
    user_email TEXT
)
""")
connection.commit()
# Certificates Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS certificates(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    certificate_name TEXT NOT NULL,
    issuer TEXT NOT NULL,
    issue_date TEXT NOT NULL,
    credential_link TEXT,
    user_email TEXT NOT NULL
)
""")

connection.commit()
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        fullname = request.form["fullname"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        try:
            cursor.execute("""
            INSERT INTO users(fullname, email, password)
            VALUES (?, ?, ?)
            """, (fullname, email, hashed_password))

            connection.commit()

            print("User Registered Successfully")

            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            return "Email already exists"

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        cursor.execute("""
        SELECT * FROM users
        WHERE email = ?
        """, (email,))

        user = cursor.fetchone()

        if user and check_password_hash(user[3], password):
            session["user"] = user[2]    
            return redirect(url_for("dashboard"))
        else:
            return "Invalid Email or Password"

    return render_template("login.html")

@app.route("/users")
def users():

    cursor.execute("SELECT * FROM users")

    data = cursor.fetchall()

    return str(data)

@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect(url_for("login"))

    # Total Skills
    cursor.execute("""
        SELECT COUNT(*)
        FROM skills
        WHERE user_email=?
    """,(session["user"],))

    total_skills = cursor.fetchone()[0]

    # Total Projects
    cursor.execute("""
        SELECT COUNT(*)
        FROM projects
        WHERE user_email=?
    """,(session["user"],))

    total_projects = cursor.fetchone()[0]

    # Average Skill Progress
    cursor.execute("""
        SELECT AVG(progress)
        FROM skills
        WHERE user_email=?
    """,(session["user"],))

    avg_skill = cursor.fetchone()[0]

    if avg_skill is None:
        avg_skill = 0

    avg_skill = round(avg_skill)

    return render_template(
        "dashboard.html",
        user=session["user"],
        total_skills=total_skills,
        total_projects=total_projects,
        avg_skill=avg_skill
    )

@app.route("/logout")
def logout():

    session.pop("user", None)

    return redirect(url_for("login"))

@app.route("/add_skill")
def add_skill():
    return render_template("add_skill.html")
@app.route("/skills")
def skills():

    cursor.execute("SELECT * FROM skills")

    data = cursor.fetchall()

    return str(data)
@app.route("/add_project", methods=["GET", "POST"])
def add_project():

    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        project_name = request.form["project_name"]
        tech_stack = request.form["tech_stack"]
        description = request.form["description"]
        github_link = request.form["github_link"]
        live_link = request.form["live_link"]
        status = request.form["status"]
        progress = request.form["progress"]

        cursor.execute("""
            INSERT INTO projects(
                project_name,
                tech_stack,
                description,
                github_link,
                live_link,
                status,
                progress,
                user_email
            )
            VALUES(?,?,?,?,?,?,?,?)
        """,(
            project_name,
            tech_stack,
            description,
            github_link,
            live_link,
            status,
            progress,
            session["user"]
        ))

        connection.commit()

        return redirect(url_for("my_projects"))

    return render_template("add_project.html")
@app.route("/my_projects")
def my_projects():

    if "user" not in session:
        return redirect(url_for("login"))

    cursor.execute("""
        SELECT
            id,
            project_name,
            tech_stack,
            description,
            github_link,
            live_link,
            status,
            progress
        FROM projects
        WHERE user_email = ?
    """, (session["user"],))

    projects = cursor.fetchall()

    return render_template(
        "my_projects.html",
        projects=projects,
        user=session["user"]
    )
@app.route("/delete_project/<int:id>")
def delete_project(id):

    if "user" not in session:
        return redirect(url_for("login"))

    cursor.execute("""
        DELETE FROM projects
        WHERE id = ?
        AND user_email = ?
    """, (id, session["user"]))

    connection.commit()

    return redirect(url_for("my_projects"))
@app.route("/edit_project/<int:id>", methods=["GET", "POST"])
def edit_project(id):

    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        project_name = request.form["project_name"]
        tech_stack = request.form["tech_stack"]
        description = request.form["description"]
        github_link = request.form["github_link"]
        live_link = request.form["live_link"]
        status = request.form["status"]
        progress = request.form["progress"]

        cursor.execute("""
            UPDATE projects
            SET project_name=?,
                tech_stack=?,
                description=?,
                github_link=?,
                live_link=?,
                status=?,
                progress=?
            WHERE id=?
            AND user_email=?
        """, (
            project_name,
            tech_stack,
            description,
            github_link,
            live_link,
            status,
            progress,
            id,
            session["user"]
        ))

        connection.commit()

        return redirect(url_for("my_projects"))

    cursor.execute("""
        SELECT *
        FROM projects
        WHERE id=?
        AND user_email=?
    """, (id, session["user"]))

    project = cursor.fetchone()

    return render_template(
        "edit_project.html",
        project=project
    )
@app.route("/save_skill", methods=["POST"])
def save_skill():

    if "user" not in session:
        return redirect(url_for("login"))

    skill_name = request.form["skill_name"]
    category = request.form["category"]
    level = request.form["level"]
    progress = request.form["progress"]

    cursor.execute("""
        INSERT INTO skills
        (skill_name, category, level, progress, user_email)
        VALUES (?, ?, ?, ?, ?)
    """, (
        skill_name,
        category,
        level,
        progress,
        session["user"]
    ))

    connection.commit()

    return redirect(url_for("dashboard"))
@app.route("/my_skills")
def my_skills():

    if "user" not in session:
        return redirect(url_for("login"))

    cursor.execute("""
        SELECT id, skill_name, category, level, progress
        FROM skills
        WHERE user_email = ?
    """, (session["user"],))

    skills = cursor.fetchall()

    return render_template(
        "my_skills.html",
        user=session["user"],
        skills=skills
    )
@app.route("/delete_skill/<int:id>")
def delete_skill(id):

    if "user" not in session:
        return redirect(url_for("login"))

    cursor.execute("""
        DELETE FROM skills
        WHERE id = ?
        AND user_email = ?
    """, (id, session["user"]))

    connection.commit()

    return redirect(url_for("my_skills"))
@app.route("/edit_skill/<int:id>", methods=["GET", "POST"])
def edit_skill(id):

    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        skill_name = request.form["skill_name"]
        category = request.form["category"]
        level = request.form["level"]
        progress = request.form["progress"]

        cursor.execute("""
            UPDATE skills
            SET skill_name=?,
                category=?,
                level=?,
                progress=?
            WHERE id=?
            AND user_email=?
        """, (
            skill_name,
            category,
            level,
            progress,
            id,
            session["user"]
        ))

        connection.commit()

        return redirect(url_for("my_skills"))

    cursor.execute("""
        SELECT *
        FROM skills
        WHERE id=?
        AND user_email=?
    """, (id, session["user"]))

    skill = cursor.fetchone()

    return render_template("edit_skill.html", skill=skill)
@app.route("/test")
def test():
    return "Working"
@app.route("/profile")
def profile():

    if "user" not in session:
        return redirect(url_for("login"))

    cursor.execute("""
        SELECT *
        FROM profile
        WHERE email=?
    """, (session["user"],))

    profile = cursor.fetchone()

    return render_template(
        "profile.html",
        profile=profile
    )
@app.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():

    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        full_name = request.form["full_name"]
        phone = request.form["phone"]
        college = request.form["college"]
        department = request.form["department"]
        semester = request.form["semester"]
        location = request.form["location"]
        github = request.form["github"]
        linkedin = request.form["linkedin"]
        portfolio = request.form["portfolio"]
        bio = request.form["bio"]

        cursor.execute("""
            SELECT *
            FROM profile
            WHERE email=?
        """, (session["user"],))

        existing = cursor.fetchone()

        if existing:

            cursor.execute("""
                UPDATE profile
                SET full_name=?,
                    phone=?,
                    college=?,
                    department=?,
                    semester=?,
                    location=?,
                    github=?,
                    linkedin=?,
                    portfolio=?,
                    bio=?
                WHERE email=?
            """, (
                full_name,
                phone,
                college,
                department,
                semester,
                location,
                github,
                linkedin,
                portfolio,
                bio,
                session["user"]
            ))

        else:

            cursor.execute("""
                INSERT INTO profile(
                    full_name,
                    email,
                    phone,
                    college,
                    department,
                    semester,
                    location,
                    github,
                    linkedin,
                    portfolio,
                    bio
                )
                VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """, (
                full_name,
                session["user"],
                phone,
                college,
                department,
                semester,
                location,
                github,
                linkedin,
                portfolio,
                bio
            ))

        connection.commit()

        return redirect(url_for("dashboard"))
    cursor.execute("""
        SELECT *
        FROM profile
        WHERE email=?
    """, (session["user"],))

    profile = cursor.fetchone()

    return render_template(
    "edit_profile.html",
    profile=profile
)

@app.route("/resume")
def resume():

    if "user" not in session:
        return redirect(url_for("login"))

    cursor.execute("""
        SELECT *
        FROM profile
        WHERE email=?
    """, (session["user"],))
    profile = cursor.fetchone()

    cursor.execute("""
        SELECT *
        FROM skills
        WHERE user_email=?
    """, (session["user"],))
    skills = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM projects
        WHERE user_email=?
    """, (session["user"],))
    projects = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM certificates
        WHERE user_email=?
    """, (session["user"],))
    certificates = cursor.fetchall()

    return render_template(
        "resume.html",
        profile=profile,
        skills=skills,
        projects=projects,
        certificates=certificates
    )

@app.route("/resume_preview")
def resume_preview():

    if "user" not in session:
        return redirect(url_for("login"))

    cursor.execute("""
        SELECT *
        FROM profile
        WHERE email=?
    """, (session["user"],))
    profile = cursor.fetchone()

    cursor.execute("""
        SELECT *
        FROM skills
        WHERE user_email=?
    """, (session["user"],))
    skills = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM projects
        WHERE user_email=?
    """, (session["user"],))
    projects = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM certificates
        WHERE user_email=?
    """, (session["user"],))
    certificates = cursor.fetchall()

    return render_template(
        "resume_preview.html",
        profile=profile,
        skills=skills,
        projects=projects,
        certificates=certificates
    )
@app.route("/add_certificate", methods=["GET", "POST"])
def add_certificate():

    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        certificate_name = request.form["certificate_name"]
        issuer = request.form["issuer"]
        issue_date = request.form["issue_date"]
        credential_link = request.form["credential_link"]

        cursor.execute("""
            INSERT INTO certificates(
                certificate_name,
                issuer,
                issue_date,
                credential_link,
                user_email
            )
            VALUES(?,?,?,?,?)
        """, (
            certificate_name,
            issuer,
            issue_date,
            credential_link,
            session["user"]
        ))

        connection.commit()

        return redirect(url_for("my_certificates"))

    return render_template("add_certificate.html")
@app.route("/my_certificates")
def my_certificates():

    if "user" not in session:
        return redirect(url_for("login"))

    cursor.execute("""
        SELECT *
        FROM certificates
        WHERE user_email=?
    """, (session["user"],))

    certificates = cursor.fetchall()

    return render_template(
        "my_certificates.html",
        certificates=certificates
    )
@app.route("/delete_certificate/<int:id>")
def delete_certificate(id):

    if "user" not in session:
        return redirect(url_for("login"))

    cursor.execute("""
        DELETE FROM certificates
        WHERE id=?
        AND user_email=?
    """, (id, session["user"]))

    connection.commit()

    return redirect(url_for("my_certificates"))
@app.route("/edit_certificate/<int:id>", methods=["GET", "POST"])
def edit_certificate(id):

    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        certificate_name = request.form["certificate_name"]
        issuer = request.form["issuer"]
        issue_date = request.form["issue_date"]
        credential_link = request.form["credential_link"]

        cursor.execute("""
            UPDATE certificates
            SET certificate_name=?,
                issuer=?,
                issue_date=?,
                credential_link=?
            WHERE id=?
            AND user_email=?
        """,(
            certificate_name,
            issuer,
            issue_date,
            credential_link,
            id,
            session["user"]
        ))

        connection.commit()

        return redirect(url_for("my_certificates"))

    cursor.execute("""
        SELECT *
        FROM certificates
        WHERE id=?
        AND user_email=?
    """, (id, session["user"]))

    certificate = cursor.fetchone()

    return render_template(
        "edit_certificate.html",
        certificate=certificate
    )
@app.route("/resume-analyzer", methods=["GET", "POST"])
def resume_analyzer():

    extracted_text = ""

    if request.method == "POST":

        action = request.form.get("action")
        print("Action =", action)

        # ---------------- Resume Analyzer ----------------
        if action == "resume":

            resume = request.files.get("resume")

            if resume:

                filename = secure_filename(resume.filename)

                filepath = os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                )

                resume.save(filepath)

                reader = easyocr.Reader(['en'])

                doc = fitz.open(filepath)

                for page in doc:

                    text = page.get_text()

                    if text.strip():

                        extracted_text += text + "\n"

                    else:

                        pix = page.get_pixmap(dpi=300)

                        img_bytes = pix.tobytes("png")

                        image = Image.open(io.BytesIO(img_bytes))
                        image = np.array(image)

                        result = reader.readtext(image)

                        for item in result:
                            extracted_text += item[1] + " "

                doc.close()

                session["resume_text"] = extracted_text

                text = extracted_text.lower()

                resume_score = 0
                ats_score = 0

                strengths = []
                suggestions = []

                keywords = [
                    "python",
                    "java",
                    "c",
                    "sql",
                    "html",
                    "css",
                    "javascript",
                    "react",
                    "node",
                    "flask",
                    "django",
                    "github",
                    "linkedin",
                    "education",
                    "project",
                    "projects",
                    "skills",
                    "experience",
                    "internship"
                ]

                for word in keywords:

                    if word in text:
                        resume_score += 5

                resume_score = min(resume_score, 100)
                ats_score = resume_score

                if "python" in text:
                    strengths.append("Python Skill Present")

                if "github" in text:
                    strengths.append("GitHub Profile Added")

                if "linkedin" in text:
                    strengths.append("LinkedIn Profile Present")

                if "education" in text:
                    strengths.append("Education Section Present")

                if "experience" in text:
                    strengths.append("Experience Section Present")

                if "project" in text:
                    strengths.append("Projects Section Present")

                if "linkedin" not in text:
                    suggestions.append("Add LinkedIn Profile")

                if "github" not in text:
                    suggestions.append("Add GitHub Profile")

                if "internship" not in text:
                    suggestions.append("Mention Internship Experience")

                if "achievement" not in text:
                    suggestions.append("Add Achievements Section")

                if len(text) < 1000:
                    suggestions.append(
                        "Resume can include more technical details"
                    )

                return render_template(
                    "resume_analyzer.html",
                    extracted_text=extracted_text,
                    resume_score=resume_score,
                    ats_score=ats_score,
                    strengths=strengths,
                    suggestions=suggestions,
                    skill_match=None,
                    existing_skills=[],
                    missing_skills=[],
                    roadmap=[],
                    projects=[],
                    certifications=[],
                    tools=[],
                    interview_topics=[]
                )

        # ---------------- Skill Gap ----------------
        elif action == "skill_gap":

            job_role = request.form["job_role"].strip()

            data = career_data.get(job_role)

            if not data:

                return render_template(
                    "resume_analyzer.html",
                    extracted_text="Resume Already Analyzed",
                    resume_score=0,
                    ats_score=0,
                    strengths=[],
                    suggestions=["Please select a valid job role."],
                    skill_match=0,
                    existing_skills=[],
                    missing_skills=[],
                    roadmap=[],
                    projects=[],
                    certifications=[],
                    tools=[],
                    interview_topics=[]
                )

            resume_text = session.get("resume_text", "").lower()

            required_skills = data["required_skills"]

            existing_skills = [
                skill
                for skill in required_skills
                if skill.lower() in resume_text
            ]

            missing_skills = [
                skill
                for skill in required_skills
                if skill.lower() not in resume_text
            ]
            if required_skills:
                skill_match = round(
                    (len(existing_skills) / len(required_skills)) * 100
                )
            else:
                skill_match = 0

            roadmap = data["roadmap"]
            projects = data["projects"]
            certifications = data["certifications"]
            tools = data["tools"]
            interview_topics = data["interview_topics"]

            return render_template(
                "resume_analyzer.html",
                extracted_text="Resume Already Analyzed",
                resume_score=82,
                ats_score=82,
                strengths=[],
                suggestions=[],
                skill_match=skill_match,
                existing_skills=existing_skills,
                missing_skills=missing_skills,
                roadmap=roadmap,
                projects=projects,
                certifications=certifications,
                tools=tools,
                interview_topics=interview_topics
            )

    return render_template(
        "resume_analyzer.html",
        extracted_text="",
        resume_score=0,
        ats_score=0,
        strengths=[],
        suggestions=[],
        skill_match=None,
        existing_skills=[],
        missing_skills=[],
        roadmap=[],
        projects=[],
        certifications=[],
        tools=[],
        interview_topics=[]
    )
@app.route("/gemini-test")
def gemini_test():

    response = model.generate_content(
        "Say Hello from Gemini in one sentence."
    )

    return response.text
@app.route("/check-key")
def check_key():
    key = os.getenv("GEMINI_API_KEY")

    if key:
        return f"Loaded key starts with: {key[:10]}"
    else:
        return "No API key loaded!"
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)