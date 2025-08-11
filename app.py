from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for, session, flash
from flask_cors import CORS
import os
import json
import PyPDF2
import docx
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import openai
from transformers import pipeline
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io
import sqlite3
from functools import wraps

app = Flask(__name__)
CORS(app)
app.secret_key = 'your-secret-key-change-this-in-production'

# Configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
def init_db():
    conn = sqlite3.connect('talentmate.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            role TEXT DEFAULT 'user',
            phone TEXT,
            company TEXT,
            position TEXT,
            experience_years INTEGER,
            skills TEXT,
            bio TEXT,
            profile_picture TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS interview_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_id TEXT UNIQUE,
            job_role TEXT,
            resume_data TEXT,
            questions TEXT,
            answers TEXT,
            scores TEXT,
            overall_score INTEGER,
            status TEXT DEFAULT 'completed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS interview_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_id TEXT,
            preferred_date DATETIME,
            preferred_time TEXT,
            message TEXT,
            status TEXT DEFAULT 'pending',
            recruiter_id INTEGER,
            recruiter_response TEXT,
            scheduled_date DATETIME,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (recruiter_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# User management functions
def create_user(username, email, password, full_name):
    conn = sqlite3.connect('talentmate.db')
    cursor = conn.cursor()
    password_hash = generate_password_hash(password)
    try:
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, full_name)
            VALUES (?, ?, ?, ?)
        ''', (username, email, password_hash, full_name))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        conn.close()
        return None

def verify_user(username, password):
    conn = sqlite3.connect('talentmate.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, password_hash FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    if user and check_password_hash(user[1], password):
        return user[0]
    return None

def get_user_info(user_id):
    conn = sqlite3.connect('talentmate.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT username, email, full_name, role, phone, company, position, 
               experience_years, skills, bio, profile_picture, created_at 
        FROM users WHERE id = ?
    ''', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

# Initialize NLP models
try:
    sentiment_analyzer = pipeline("sentiment-analysis")
    print("NLP models loaded successfully")
except Exception as e:
    print(f"Error loading NLP models: {e}")
    sentiment_analyzer = None

# Download required NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
except:
    pass

class SkillMateAI:
    def __init__(self):
        self.question_bank = {
            "coding": {
                "beginner": [
                    "Write a function to reverse a string without using built-in reverse methods.",
                    "Implement a function to check if a number is prime.",
                    "Write a program to find the factorial of a number using recursion.",
                    "Create a function to find the largest element in an array.",
                    "Implement a simple calculator that can add, subtract, multiply, and divide."
                ],
                "intermediate": [
                    "Implement a binary search algorithm and explain its time complexity.",
                    "Write a function to detect if a linked list has a cycle.",
                    "Implement a stack using arrays and demonstrate its operations.",
                    "Create a function to find all permutations of a string.",
                    "Write a program to implement merge sort algorithm."
                ],
                "advanced": [
                    "Design and implement a LRU (Least Recently Used) cache.",
                    "Implement a trie data structure for autocomplete functionality.",
                    "Write a function to find the shortest path in a weighted graph using Dijkstra's algorithm.",
                    "Design a system to handle millions of concurrent users.",
                    "Implement a distributed hash table with consistent hashing."
                ]
            },
            "role_specific": {
                "salesforce_admin": [
                    "How would you design a custom object structure for a sales pipeline tracking system in Salesforce?",
                    "Explain the difference between Role Hierarchy and Sharing Rules. When would you use each?",
                    "Walk me through creating a validation rule to ensure data quality in opportunity records.",
                    "How would you set up an approval process for expense reports with multiple approval levels?",
                    "Describe how you would use Process Builder vs Flow vs Workflow Rules for automation.",
                    "How would you handle data migration from a legacy CRM to Salesforce while maintaining data integrity?",
                    "Explain how you would configure territory management for a global sales organization.",
                    "How would you create custom reports and dashboards to track sales performance KPIs?"
                ],
                "salesforce_developer": [
                    "Write an Apex trigger to prevent duplicate account creation based on email domain.",
                    "How would you implement bulk data processing in Apex while avoiding governor limits?",
                    "Explain the difference between SOQL and SOSL. Provide examples of when to use each.",
                    "Design a Lightning Web Component for a custom opportunity management interface.",
                    "How would you implement custom REST API endpoints in Salesforce for external integrations?",
                    "Describe how you would use Platform Events for real-time data synchronization.",
                    "Explain the MVC pattern in Salesforce development and how it applies to Lightning components.",
                    "How would you optimize SOQL queries for better performance in large data sets?"
                ],
                "program_analyst": [
                    "How would you approach analyzing business requirements for a new software implementation?",
                    "Describe your process for conducting stakeholder interviews to gather functional requirements.",
                    "How would you create and maintain a requirements traceability matrix for a large project?",
                    "Explain how you would perform gap analysis between current state and future state processes.",
                    "How would you facilitate workshops to resolve conflicting requirements from different departments?",
                    "Describe your approach to creating user stories and acceptance criteria for development teams.",
                    "How would you measure and report on project KPIs and success metrics?",
                    "Explain how you would conduct risk assessment and mitigation planning for program initiatives."
                ],
                "java_fullstack": [
                    "Design a RESTful API using Spring Boot for a microservices architecture.",
                    "Explain the difference between @Component, @Service, and @Repository annotations in Spring.",
                    "How would you implement JWT-based authentication in a Spring Boot application?",
                    "Describe how you would optimize JPA/Hibernate queries for better database performance.",
                    "How would you implement caching strategies using Redis in a Java application?",
                    "Explain how you would handle concurrent requests and thread safety in a Java web application.",
                    "Describe the implementation of a message queue system using RabbitMQ or Apache Kafka.",
                    "How would you implement unit testing for a Spring Boot application using JUnit and Mockito?"
                ],
                "python_fullstack": [
                    "Design a RESTful API using Django REST Framework with proper serialization and validation.",
                    "Explain how you would implement async/await patterns in Python for handling concurrent requests.",
                    "How would you structure a Django project for scalability and maintainability?",
                    "Describe how you would implement caching strategies using Redis with Django.",
                    "How would you handle database migrations and schema changes in a production Django application?",
                    "Explain how you would implement OAuth2 authentication using Django and social auth.",
                    "Describe how you would optimize Python code for better performance in data-heavy applications.",
                    "How would you implement background task processing using Celery with Django?"
                ],
                "dotnet_fullstack": [
                    "Design a Web API using ASP.NET Core with proper dependency injection and middleware.",
                    "Explain the difference between .NET Core and .NET Framework, and when to use each.",
                    "How would you implement Entity Framework Core with Code First migrations?",
                    "Describe how you would implement authentication and authorization using ASP.NET Core Identity.",
                    "How would you handle error handling and logging in a .NET Core application?",
                    "Explain how you would implement SignalR for real-time communication features.",
                    "Describe how you would optimize .NET applications for performance and memory management.",
                    "How would you implement unit testing using xUnit and Moq in a .NET Core project?"
                ]
            },
            "scenario": {
                "leadership": [
                    "Describe a time when you had to lead a team through a difficult project. How did you motivate your team?",
                    "How would you handle a situation where team members have conflicting opinions on a technical approach?",
                    "Tell me about a time when you had to make a difficult decision with limited information.",
                    "How do you ensure effective communication within your team?",
                    "Describe how you would handle an underperforming team member."
                ],
                "problem_solving": [
                    "Walk me through how you would debug a system that's running slowly in production.",
                    "How would you approach designing a new feature with unclear requirements?",
                    "Describe a complex technical problem you solved and your approach.",
                    "How do you prioritize tasks when everything seems urgent?",
                    "Tell me about a time when you had to learn a new technology quickly."
                ],
                "communication": [
                    "How would you explain a complex technical concept to a non-technical stakeholder?",
                    "Describe a time when you had to give difficult feedback to a colleague.",
                    "How do you handle disagreements during code reviews?",
                    "Tell me about a presentation you gave and how you prepared for it.",
                    "How do you ensure your written communication is clear and effective?"
                ],
                "salesforce_specific": [
                    "How would you explain the benefits of Salesforce automation to a non-technical business user?",
                    "Describe a time when you had to troubleshoot a complex Salesforce integration issue.",
                    "How would you approach training end users on a new Salesforce feature you implemented?",
                    "Tell me about a time when you had to balance technical constraints with business requirements.",
                    "How would you handle a situation where a business user requests a customization that goes against best practices?"
                ],
                "analyst_specific": [
                    "Describe how you would handle conflicting requirements from different stakeholders.",
                    "How would you approach documenting complex business processes for technical implementation?",
                    "Tell me about a time when your analysis revealed unexpected insights that changed project direction.",
                    "How would you present technical recommendations to executive-level stakeholders?",
                    "Describe your approach to quality assurance and testing coordination."
                ]
            }
        }
        
    def extract_text_from_pdf(self, file_path):
        """Extract text from PDF file"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                return text
        except Exception as e:
            print(f"Error extracting PDF text: {e}")
            return ""
    
    def extract_text_from_docx(self, file_path):
        """Extract text from DOCX file"""
        try:
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            print(f"Error extracting DOCX text: {e}")
            return ""
    
    def parse_resume(self, file_path):
        """Parse resume and extract key information"""
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.pdf':
            text = self.extract_text_from_pdf(file_path)
        elif file_extension == '.docx':
            text = self.extract_text_from_docx(file_path)
        else:
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()
        
        # Simple keyword extraction for skills and experience
        skills_keywords = ['python', 'java', 'javascript', 'react', 'angular', 'node.js', 'sql', 'mongodb', 
                          'aws', 'docker', 'kubernetes', 'git', 'machine learning', 'ai', 'data science']
        
        found_skills = []
        text_lower = text.lower()
        
        for skill in skills_keywords:
            if skill in text_lower:
                found_skills.append(skill)
        
        # Estimate experience level based on keywords
        experience_indicators = {
            'senior': ['senior', 'lead', 'architect', 'principal', 'manager'],
            'mid': ['experienced', 'specialist', 'developer', '3+ years', '4+ years', '5+ years'],
            'junior': ['junior', 'entry', 'graduate', 'intern', 'trainee']
        }
        
        experience_level = 'intermediate'  # default
        for level, keywords in experience_indicators.items():
            if any(keyword in text_lower for keyword in keywords):
                experience_level = level
                break
        
        return {
            'skills': found_skills,
            'experience_level': experience_level,
            'full_text': text
        }
    
    def detect_role_category(self, job_role):
        """Detect the specific role category based on job title"""
        job_role_lower = job_role.lower()
        
        # Salesforce roles
        if 'salesforce' in job_role_lower:
            if any(keyword in job_role_lower for keyword in ['developer', 'dev', 'apex', 'lightning']):
                return 'salesforce_developer'
            else:
                return 'salesforce_admin'
        
        # Analyst roles
        if any(keyword in job_role_lower for keyword in ['analyst', 'business analyst', 'program analyst', 'systems analyst']):
            return 'program_analyst'
        
        # Full Stack Developer roles
        if 'full stack' in job_role_lower or 'fullstack' in job_role_lower:
            if any(keyword in job_role_lower for keyword in ['java', 'spring', 'hibernate']):
                return 'java_fullstack'
            elif any(keyword in job_role_lower for keyword in ['python', 'django', 'flask']):
                return 'python_fullstack'
            elif any(keyword in job_role_lower for keyword in ['.net', 'dotnet', 'c#', 'asp.net']):
                return 'dotnet_fullstack'
        
        # Technology-specific roles
        if any(keyword in job_role_lower for keyword in ['java', 'spring', 'hibernate']) and 'developer' in job_role_lower:
            return 'java_fullstack'
        elif any(keyword in job_role_lower for keyword in ['python', 'django', 'flask']) and 'developer' in job_role_lower:
            return 'python_fullstack'
        elif any(keyword in job_role_lower for keyword in ['.net', 'dotnet', 'c#', 'asp.net']) and 'developer' in job_role_lower:
            return 'dotnet_fullstack'
        
        return None

    def generate_questions(self, resume_data, job_role, num_questions=5):
        """Generate interview questions based on resume and job role"""
        experience_level = resume_data['experience_level']
        skills = resume_data['skills']
        role_category = self.detect_role_category(job_role)
        
        # Map experience levels
        if experience_level == 'senior':
            coding_level = 'advanced'
        elif experience_level == 'junior':
            coding_level = 'beginner'
        else:
            coding_level = 'intermediate'
        
        all_questions = []
        
        # If we have role-specific questions, use them
        if role_category and role_category in self.question_bank['role_specific']:
            role_questions = np.random.choice(
                self.question_bank['role_specific'][role_category],
                size=min(3, len(self.question_bank['role_specific'][role_category])),
                replace=False
            ).tolist()
            
            # Format role-specific questions
            for i, q in enumerate(role_questions):
                all_questions.append({
                    'id': f'role_{i+1}',
                    'type': 'role_specific',
                    'question': q,
                    'category': f'{role_category.replace("_", " ").title()} Specific'
                })
        else:
            # Fallback to general coding questions
            coding_questions = np.random.choice(
                self.question_bank['coding'][coding_level], 
                size=min(3, len(self.question_bank['coding'][coding_level])), 
                replace=False
            ).tolist()
            
            # Format coding questions
            for i, q in enumerate(coding_questions):
                all_questions.append({
                    'id': f'coding_{i+1}',
                    'type': 'coding',
                    'question': q,
                    'category': 'Technical Coding'
                })
        
        # Select scenario questions based on role
        scenario_categories = []
        if role_category in ['salesforce_admin', 'salesforce_developer']:
            scenario_categories = ['salesforce_specific', 'problem_solving']
        elif role_category == 'program_analyst':
            scenario_categories = ['analyst_specific', 'communication']
        else:
            scenario_categories = ['problem_solving', 'communication']
        
        # Add leadership scenarios for senior roles
        if experience_level == 'senior':
            scenario_categories.append('leadership')
        
        selected_scenarios = []
        for category in scenario_categories[:2]:  # Take first 2 categories
            if category in self.question_bank['scenario']:
                questions = self.question_bank['scenario'][category]
                selected_scenarios.extend(
                    np.random.choice(questions, size=1, replace=False).tolist()
                )
        
        # Format scenario questions
        for i, q in enumerate(selected_scenarios):
            all_questions.append({
                'id': f'scenario_{i+1}',
                'type': 'scenario', 
                'question': q,
                'category': 'Behavioral/Scenario'
            })
        
        return all_questions[:num_questions]  # Ensure we don't exceed requested number
    
    def score_answer(self, question, answer, question_type):
        """Score the answer using NLP techniques"""
        if not answer or len(answer.strip()) < 10:
            return {
                'score': 0,
                'feedback': 'Answer is too short. Please provide a more detailed response.',
                'areas_to_improve': ['Provide more detailed explanations', 'Include specific examples']
            }
        
        # Basic scoring criteria
        score = 0
        feedback_points = []
        areas_to_improve = []
        
        # Length and detail analysis
        word_count = len(answer.split())
        if word_count >= 50:
            score += 20
            feedback_points.append("Good level of detail in response")
        elif word_count >= 25:
            score += 10
            areas_to_improve.append("Provide more detailed explanations")
        else:
            areas_to_improve.append("Increase response length and detail")
        
        # Technical keywords for coding questions
        if question_type == 'coding':
            technical_keywords = ['algorithm', 'complexity', 'time', 'space', 'data structure', 
                                'variable', 'function', 'loop', 'condition', 'efficiency']
            keyword_count = sum(1 for keyword in technical_keywords if keyword.lower() in answer.lower())
            
            if keyword_count >= 3:
                score += 30
                feedback_points.append("Good use of technical terminology")
            elif keyword_count >= 1:
                score += 15
                areas_to_improve.append("Include more technical terminology")
            else:
                areas_to_improve.append("Use more technical language and concepts")
        
        # Role-specific technical scoring
        elif question_type == 'role_specific':
            # Define role-specific keywords
            role_keywords = {
                'salesforce': ['apex', 'soql', 'trigger', 'workflow', 'validation', 'lightning', 'component', 'process builder', 'flow'],
                'java': ['spring', 'hibernate', 'jpa', 'microservices', 'rest api', 'junit', 'maven', 'dependency injection'],
                'python': ['django', 'flask', 'orm', 'serializer', 'middleware', 'celery', 'rest framework', 'async'],
                'dotnet': ['asp.net', 'entity framework', 'mvc', 'web api', 'dependency injection', 'middleware', 'linq'],
                'analyst': ['requirements', 'stakeholder', 'user story', 'acceptance criteria', 'gap analysis', 'process', 'kpi']
            }
            
            # Determine which keywords to use based on the question context
            applicable_keywords = []
            answer_lower = answer.lower()
            
            for role, keywords in role_keywords.items():
                if any(keyword in answer_lower for keyword in keywords):
                    applicable_keywords.extend(keywords)
                    break
            
            # If no specific role keywords found, use general technical terms
            if not applicable_keywords:
                applicable_keywords = ['solution', 'implementation', 'design', 'architecture', 'best practice', 
                                     'optimization', 'integration', 'configuration', 'development', 'testing']
            
            keyword_count = sum(1 for keyword in applicable_keywords if keyword in answer_lower)
            
            if keyword_count >= 4:
                score += 35
                feedback_points.append("Excellent use of role-specific technical knowledge")
            elif keyword_count >= 2:
                score += 20
                feedback_points.append("Good technical understanding demonstrated")
            elif keyword_count >= 1:
                score += 10
                areas_to_improve.append("Include more specific technical details and terminology")
            else:
                areas_to_improve.append("Demonstrate deeper technical knowledge and use specific terminology")
        
        # Scenario-based scoring
        elif question_type == 'scenario':
            scenario_keywords = ['experience', 'situation', 'approach', 'result', 'learned', 
                               'challenge', 'solution', 'team', 'communication']
            keyword_count = sum(1 for keyword in scenario_keywords if keyword.lower() in answer.lower())
            
            if keyword_count >= 3:
                score += 30
                feedback_points.append("Good storytelling and situation description")
            elif keyword_count >= 1:
                score += 15
                areas_to_improve.append("Include more specific examples and outcomes")
            else:
                areas_to_improve.append("Provide concrete examples and specific situations")
        
        # Structure and clarity
        sentences = answer.split('.')
        if len(sentences) >= 3:
            score += 20
            feedback_points.append("Well-structured response")
        else:
            areas_to_improve.append("Improve response structure and organization")
        
        # Sentiment analysis (if available)
        if sentiment_analyzer:
            try:
                sentiment = sentiment_analyzer(answer[:512])  # Limit text length
                if sentiment[0]['label'] == 'POSITIVE' and sentiment[0]['score'] > 0.6:
                    score += 15
                    feedback_points.append("Positive and confident tone")
                elif sentiment[0]['score'] < 0.3:
                    areas_to_improve.append("Show more confidence in your response")
            except:
                pass
        
        # Cap score at 100
        score = min(score, 100)
        
        # Generate overall feedback
        if score >= 80:
            overall = "Excellent response! "
        elif score >= 60:
            overall = "Good response with room for improvement. "
        elif score >= 40:
            overall = "Average response. "
        else:
            overall = "Needs significant improvement. "
        
        feedback = overall + " ".join(feedback_points)
        
        return {
            'score': score,
            'feedback': feedback,
            'areas_to_improve': areas_to_improve
        }

# Initialize AI system
skillmate_ai = SkillMateAI()

# User role is now stored in session during login

@app.route('/')
def index():
    # Redirect to login if user is not authenticated
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('home'))

@app.route('/home')
@login_required
def home():
    return render_template('home.html')

@app.route('/interview')
@login_required
def interview():
    return render_template('interview.html')

@app.route('/review')
@login_required
def review():
    # Get user's interview sessions
    conn = sqlite3.connect('talentmate.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT session_id, job_role, created_at 
        FROM interview_sessions 
        WHERE user_id = ? 
        ORDER BY created_at DESC
    ''', (session['user_id'],))
    sessions = cursor.fetchall()
    conn.close()
    return render_template('review.html', sessions=sessions)

@app.route('/help')
def help():
    return render_template('help.html')

# Profile Management Routes
@app.route('/profile')
@login_required
def profile():
    user_info = get_user_info(session['user_id'])
    if not user_info:
        flash('User not found', 'error')
        return redirect(url_for('home'))
    
    # Get user's interview history
    conn = sqlite3.connect('talentmate.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT session_id, job_role, overall_score, created_at, status 
        FROM interview_sessions 
        WHERE user_id = ? 
        ORDER BY created_at DESC
    ''', (session['user_id'],))
    interview_history = cursor.fetchall()
    
    # Get interview requests
    cursor.execute('''
        SELECT ir.*, u.full_name as recruiter_name
        FROM interview_requests ir
        LEFT JOIN users u ON ir.recruiter_id = u.id
        WHERE ir.user_id = ?
        ORDER BY ir.created_at DESC
    ''', (session['user_id'],))
    interview_requests = cursor.fetchall()
    
    conn.close()
    return render_template('profile.html', user=user_info, interview_history=interview_history, interview_requests=interview_requests)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        phone = request.form.get('phone')
        company = request.form.get('company')
        position = request.form.get('position')
        experience_years = request.form.get('experience_years')
        skills = request.form.get('skills')
        bio = request.form.get('bio')
        
        conn = sqlite3.connect('talentmate.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET phone = ?, company = ?, position = ?, experience_years = ?, skills = ?, bio = ?
            WHERE id = ?
        ''', (phone, company, position, experience_years, skills, bio, session['user_id']))
        conn.commit()
        conn.close()
        
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    user_info = get_user_info(session['user_id'])
    return render_template('edit_profile.html', user=user_info)

@app.route('/recruiter/dashboard')
@login_required
def recruiter_dashboard():
    # Check if user is a recruiter
    if session.get('user_role') != 'recruiter':
        flash('Access denied. Recruiter privileges required.', 'error')
        return redirect(url_for('home'))
    
    conn = sqlite3.connect('talentmate.db')
    cursor = conn.cursor()
    
    # Get all users with their latest interview scores
    cursor.execute('''
        SELECT u.id, u.full_name, u.email, u.company, u.position,
               MAX(is_session.overall_score) as best_score,
               COUNT(is_session.id) as total_interviews,
               u.created_at, u.experience_years
        FROM users u
        LEFT JOIN interview_sessions is_session ON u.id = is_session.user_id
        WHERE u.role = 'user'
        GROUP BY u.id
        ORDER BY best_score DESC NULLS LAST
    ''')
    all_users = cursor.fetchall()
    
    # Get pending interview requests
    cursor.execute('''
        SELECT ir.*, u.full_name, u.email, is_session.job_role, is_session.overall_score
        FROM interview_requests ir
        JOIN users u ON ir.user_id = u.id
        LEFT JOIN interview_sessions is_session ON ir.session_id = is_session.session_id
        WHERE ir.status = 'pending'
        ORDER BY ir.created_at DESC
    ''')
    pending_requests = cursor.fetchall()
    
    conn.close()
    return render_template('recruiter_dashboard.html', users=all_users, pending_requests=pending_requests)

@app.route('/schedule_interview', methods=['POST'])
@login_required
def schedule_interview():
    session_id = request.form.get('session_id')
    preferred_date = request.form.get('preferred_date')
    preferred_time = request.form.get('preferred_time')
    message = request.form.get('message', '')
    
    if not session_id or not preferred_date or not preferred_time:
        flash('Please fill in all required fields', 'error')
        return redirect(url_for('profile'))
    
    conn = sqlite3.connect('talentmate.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO interview_requests (user_id, session_id, preferred_date, preferred_time, message)
        VALUES (?, ?, ?, ?, ?)
    ''', (session['user_id'], session_id, preferred_date, preferred_time, message))
    conn.commit()
    conn.close()
    
    flash('Interview request submitted successfully!', 'success')
    return redirect(url_for('profile'))

@app.route('/manage_interview_request/<int:request_id>', methods=['POST'])
@login_required
def manage_interview_request(request_id):
    action = request.form.get('action')
    recruiter_response = request.form.get('recruiter_response', '')
    
    # Check if user is a recruiter
    if session.get('user_role') != 'recruiter':
        flash('Access denied. Recruiter privileges required.', 'error')
        return redirect(url_for('home'))
    
    conn = sqlite3.connect('talentmate.db')
    cursor = conn.cursor()
    
    if action == 'approve':
        scheduled_date = request.form.get('scheduled_date')
        cursor.execute('''
            UPDATE interview_requests 
            SET status = 'approved', recruiter_id = ?, recruiter_response = ?, 
                scheduled_date = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (session['user_id'], recruiter_response, scheduled_date, request_id))
        flash('Interview request approved!', 'success')
    elif action == 'reject':
        cursor.execute('''
            UPDATE interview_requests 
            SET status = 'rejected', recruiter_id = ?, recruiter_response = ?, 
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (session['user_id'], recruiter_response, request_id))
        flash('Interview request rejected.', 'success')
    
    conn.commit()
    conn.close()
    return redirect(url_for('recruiter_dashboard'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_id = verify_user(username, password)
        if user_id:
            session['user_id'] = user_id
            # Get user info to store role in session
            user_info = get_user_info(user_id)
            if user_info and len(user_info) > 3:
                session['user_role'] = user_info[3]
            else:
                session['user_role'] = 'user'
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Login failed. Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        if create_user(username, email, password, full_name):
            # Auto-login the new user
            user_id = verify_user(username, password)
            if user_id:
                session['user_id'] = user_id
                # Get user info to store role in session
                user_info = get_user_info(user_id)
                if user_info and len(user_info) > 3:
                    session['user_role'] = user_info[3]
                else:
                    session['user_role'] = 'user'
                flash('Account created successfully! Welcome to TalentMate!', 'success')
                return redirect(url_for('home'))
            else:
                flash('Account created! Please log in.', 'success')
                return redirect(url_for('login'))
        else:
            flash('Username or email already in use.', 'error')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/upload-resume', methods=['POST'])
@login_required
def upload_resume():
    """Handle resume upload and parsing"""
    try:
        if 'resume' not in request.files:
            return jsonify({'error': 'No resume file provided'}), 400
        
        file = request.files['resume']
        job_role = request.form.get('job_role', '')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Parse resume
        resume_data = skillmate_ai.parse_resume(filepath)
        
        # Generate questions
        questions = skillmate_ai.generate_questions(resume_data, job_role)
        
        # Store session data (in production, use proper session management)
        session_id = datetime.now().strftime("%Y%m%d%H%M%S")
        session_data = {
            'session_id': session_id,
            'resume_data': resume_data,
            'job_role': job_role,
            'questions': questions,
            'answers': {},
            'scores': {}
        }
        
        # Save session data
        conn = sqlite3.connect('talentmate.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO interview_sessions (user_id, session_id, job_role, resume_data, questions, answers, scores)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], session_id, job_role, json.dumps(resume_data), json.dumps(questions), json.dumps({}), json.dumps({})))
        conn.commit()
        conn.close()
        
        # Clean up uploaded file
        os.remove(filepath)
        
        return jsonify({
            'session_id': session_id,
            'questions': questions,
            'resume_summary': {
                'skills': resume_data['skills'],
                'experience_level': resume_data['experience_level']
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/submit-answer', methods=['POST'])
@login_required
def submit_answer():
    """Handle answer submission and scoring"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        question_id = data.get('question_id')
        answer = data.get('answer', '')
        
        # Load session data
        conn = sqlite3.connect('talentmate.db')
        cursor = conn.cursor()
        cursor.execute('SELECT questions, answers, scores FROM interview_sessions WHERE session_id = ? AND user_id = ?', (session_id, session['user_id']))
        session_data = cursor.fetchone()
        conn.close()

        if not session_data:
            return jsonify({'error': 'Session not found'}), 404
        
        questions_data = json.loads(session_data[0])
        answers_data = json.loads(session_data[1])
        scores_data = json.loads(session_data[2])
        
        # Find the question
        question_data = None
        for q in questions_data:
            if q['id'] == question_id:
                question_data = q
                break
        
        if not question_data:
            return jsonify({'error': 'Question not found'}), 404
        
        # Score the answer
        score_result = skillmate_ai.score_answer(
            question_data['question'], 
            answer, 
            question_data['type']
        )
        
        # Store answer and score
        answers_data[question_id] = answer
        scores_data[question_id] = score_result
        
        # Save updated session data
        conn = sqlite3.connect('talentmate.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE interview_sessions
            SET questions = ?, answers = ?, scores = ?
            WHERE session_id = ? AND user_id = ?
        ''', (json.dumps(questions_data), json.dumps(answers_data), json.dumps(scores_data), session_id, session['user_id']))
        conn.commit()
        conn.close()
        
        return jsonify({
            'score': score_result['score'],
            'feedback': score_result['feedback'],
            'areas_to_improve': score_result['areas_to_improve']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get-results/<session_id>')
@login_required
def get_results(session_id):
    """Get complete interview results"""
    try:
        conn = sqlite3.connect('talentmate.db')
        cursor = conn.cursor()
        cursor.execute('SELECT questions, answers, scores, job_role, resume_data FROM interview_sessions WHERE session_id = ? AND user_id = ?', (session_id, session['user_id']))
        session_data = cursor.fetchone()
        conn.close()

        if not session_data:
            return jsonify({'error': 'Session not found'}), 404
        
        questions_data = json.loads(session_data[0])
        answers_data = json.loads(session_data[1])
        scores_data = json.loads(session_data[2])
        job_role = session_data[3]
        resume_data = json.loads(session_data[4])
        
        # Calculate overall statistics
        scores = list(scores_data.values())
        if scores:
            avg_score = sum(s['score'] for s in scores) / len(scores)
            max_score = max(s['score'] for s in scores)
            min_score = min(s['score'] for s in scores)
        else:
            avg_score = max_score = min_score = 0
        
        # Collect all improvement areas
        all_improvements = []
        for score_data in scores:
            all_improvements.extend(score_data['areas_to_improve'])
        
        # Remove duplicates and get top suggestions
        unique_improvements = list(set(all_improvements))
        
        return jsonify({
            'session_id': session_id,
            'overall_score': round(avg_score, 1),
            'max_score': max_score,
            'min_score': min_score,
            'total_questions': len(questions_data),
            'answered_questions': len(answers_data),
            'detailed_scores': scores_data,
            'improvement_suggestions': unique_improvements[:5],  # Top 5
            'job_role': job_role,
            'skills_identified': resume_data['skills']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download-report/<session_id>')
@login_required
def download_report(session_id):
    """Generate and download PDF report"""
    try:
        conn = sqlite3.connect('talentmate.db')
        cursor = conn.cursor()
        cursor.execute('SELECT questions, answers, scores, job_role, resume_data FROM interview_sessions WHERE session_id = ? AND user_id = ?', (session_id, session['user_id']))
        session_data = cursor.fetchone()
        conn.close()

        if not session_data:
            return jsonify({'error': 'Session not found'}), 404
        
        questions_data = json.loads(session_data[0])
        answers_data = json.loads(session_data[1])
        scores_data = json.loads(session_data[2])
        job_role = session_data[3]
        resume_data = json.loads(session_data[4])
        
        # Create PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.darkblue
        )
        story.append(Paragraph("TalentMate Mock Interview Report", title_style))
        story.append(Spacer(1, 20))
        
        # Session info
        story.append(Paragraph(f"<b>Session ID:</b> {session_id}", styles['Normal']))
        story.append(Paragraph(f"<b>Job Role:</b> {job_role}", styles['Normal']))
        story.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Overall performance
        scores = list(scores_data.values())
        if scores:
            avg_score = sum(s['score'] for s in scores) / len(scores)
            story.append(Paragraph("Overall Performance", styles['Heading2']))
            story.append(Paragraph(f"Average Score: {avg_score:.1f}/100", styles['Normal']))
            story.append(Paragraph(f"Questions Answered: {len(answers_data)}/{len(questions_data)}", styles['Normal']))
            story.append(Spacer(1, 20))
        
        # Detailed question analysis
        story.append(Paragraph("Detailed Question Analysis", styles['Heading2']))
        
        for i, question in enumerate(questions_data):
            question_id = question['id']
            if question_id in scores_data:
                score_data = scores_data[question_id]
                
                story.append(Paragraph(f"Question {i+1}: {question['category']}", styles['Heading3']))
                story.append(Paragraph(f"<b>Q:</b> {question['question']}", styles['Normal']))
                story.append(Paragraph(f"<b>Score:</b> {score_data['score']}/100", styles['Normal']))
                story.append(Paragraph(f"<b>Feedback:</b> {score_data['feedback']}", styles['Normal']))
                
                if score_data['areas_to_improve']:
                    story.append(Paragraph("<b>Areas to Improve:</b>", styles['Normal']))
                    for improvement in score_data['areas_to_improve']:
                        story.append(Paragraph(f"• {improvement}", styles['Normal']))
                
                story.append(Spacer(1, 15))
        
        # Skills and recommendations
        story.append(Paragraph("Skills Identified", styles['Heading2']))
        skills = resume_data['skills']
        if skills:
            for skill in skills:
                story.append(Paragraph(f"• {skill.title()}", styles['Normal']))
        else:
            story.append(Paragraph("No specific technical skills identified", styles['Normal']))
        
        story.append(Spacer(1, 20))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'talentmate_interview_report_{session_id}.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting TalentMate Mock Interview System...")
    print("Access the application at http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000) 