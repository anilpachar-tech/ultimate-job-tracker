import streamlit as st
import re
import random
import hashlib
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import base64
from io import BytesIO

# ==================== SMART IMPORTS ====================

try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    from PIL import Image
    import pytesseract
    OCR_SUPPORT = True
except ImportError:
    OCR_SUPPORT = False

try:
    from twilio.rest import Client
    TWILIO_SUPPORT = True
except ImportError:
    TWILIO_SUPPORT = False

# ==================== PAGE CONFIG ====================

st.set_page_config(
    page_title="Ultimate Job Tracker",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(to right, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
    }
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-left: 5px solid #667eea;
    }
    .job-card {
        background: #f8f9fa;
        border-left: 4px solid #667eea;
        padding: 20px;
        margin: 10px 0;
        border-radius: 8px;
        transition: transform 0.2s;
    }
    .job-card:hover {
        transform: translateX(5px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .internship-card {
        background: #e3f2fd;
        border-left: 4px solid #2196F3;
        padding: 20px;
        margin: 10px 0;
        border-radius: 8px;
    }
    .skill-badge {
        display: inline-block;
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        margin: 5px;
        font-size: 0.85rem;
        font-weight: bold;
    }
    .professor-card {
        background: #f3e5f5;
        border-left: 4px solid #9c27b0;
        padding: 15px;
        margin: 10px 0;
        border-radius: 8px;
    }
    .research-area {
        background: #e1f5fe;
        color: #01579b;
        padding: 3px 10px;
        border-radius: 15px;
        font-size: 0.8rem;
        margin: 2px;
        display: inline-block;
    }
    .alert-banner {
        background: linear-gradient(to right, #ff6b6b, #ffa726);
        color: white;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
        font-weight: bold;
    }
    .cold-email-template {
        background: #f5f5f5;
        border-left: 4px solid #4caf50;
        padding: 20px;
        font-family: Georgia, serif;
        line-height: 1.6;
    }
    .filter-badge {
        background: #667eea;
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        margin: 5px;
        cursor: pointer;
    }
</style>
""", unsafe_allow_html=True)

# ==================== SESSION STATE ====================

def init_session_state():
    defaults = {
        'resume_text': '',
        'skills': [],
        'applied_jobs': [],
        'applied_internships': [],
        'auto_apply_enabled': False,
        'user_info': {
            'name': 'Anil Pachar',
            'email': '',
            'phone': '',
            'linkedin': '',
            'github': '',
            'portfolio': ''
        },
        'filters': {
            'job_type': 'All',
            'location_type': 'All',
            'experience_level': 'All',
            'work_mode': 'All'
        },
        'alerts': [],
        'saved_professors': []
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ==================== CORE FUNCTIONS ====================

def extract_pdf_text(pdf_file):
    """Extract text from PDF resume"""
    if not PDF_SUPPORT:
        return "Error: Install PyPDF2 (pip install PyPDF2)"
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

def extract_image_text(image_file):
    """Extract text from image using OCR"""
    if not OCR_SUPPORT:
        return "Error: Install pytesseract and pillow"
    try:
        image = Image.open(image_file)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        return f"OCR Error: {str(e)}"

def extract_skills(text):
    """Extract technical skills from resume"""
    if not text:
        return []
    
    text = text.lower()
    
    skill_categories = {
        'Programming': ['python', 'java', 'javascript', 'c++', 'c#', 'go', 'rust', 'ruby', 'php', 'scala'],
        'Web': ['react', 'angular', 'vue', 'node', 'django', 'flask', 'html', 'css', 'bootstrap', 'tailwind'],
        'AI/ML': ['machine learning', 'ml', 'deep learning', 'tensorflow', 'pytorch', 'keras', 'nlp', 
                 'computer vision', 'ai', 'genai', 'llm', 'langchain', 'huggingface', 'openai'],
        'Data': ['sql', 'mysql', 'postgresql', 'mongodb', 'pandas', 'numpy', 'data analysis', 
                'data science', 'tableau', 'power bi', 'excel', 'spark', 'hadoop', 'etl', 'dbt'],
        'Cloud/DevOps': ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'git', 'ci/cd', 
                        'terraform', 'ansible', 'prometheus', 'grafana'],
        'Mobile': ['android', 'ios', 'flutter', 'react native', 'kotlin', 'swift', 'dart']
    }
    
    found_skills = []
    for category, skills in skill_categories.items():
        for skill in skills:
            if skill in text:
                found_skills.append(skill)
    
    return list(set(found_skills))

def calculate_match_score(resume_text, job_desc):
    """Calculate match percentage between resume and job"""
    if not resume_text or not job_desc:
        return 0, [], []
    
    resume_skills = extract_skills(resume_text)
    job_skills = extract_skills(job_desc)
    
    if not job_skills:
        job_desc_lower = job_desc.lower()
        generic_skills = ['python', 'java', 'sql', 'aws', 'docker', 'react', 'ml', 'data']
        job_skills = [s for s in generic_skills if s in job_desc_lower]
        
        if not job_skills:
            return 50, [], ['relevant experience']
    
    matched = list(set(resume_skills) & set(job_skills))
    missing = list(set(job_skills) - set(resume_skills))
    
    score = (len(matched) / len(job_skills)) * 100 if job_skills else 0
    
    # Boosts
    if 'remote' in job_desc.lower():
        score += 5
    if 'intern' in job_desc.lower():
        score += 3
    if any(x in job_desc.lower() for x in ['iit', 'nit', 'iisc', 'research']):
        score += 10
    
    return min(score, 100), matched, missing

# ==================== PROFESSOR DATABASE ====================

PROFESSOR_DB = {
    "IIT Bombay": [
        {
            "name": "Prof. Ganesh Ramakrishnan",
            "department": "Computer Science",
            "research": ["Machine Learning", "NLP", "Information Retrieval", "Deep Learning"],
            "email": "ganesh@cse.iitb.ac.in",
            "lab": "KReSIT Lab",
            "projects": "LLMs for Indian Languages, Document Analysis",
            "url": "https://www.cse.iitb.ac.in/~ganesh/"
        },
        {
            "name": "Prof. Soumen Chakrabarti",
            "department": "Computer Science",
            "research": ["Web Mining", "Network Analysis", "Graph Neural Networks"],
            "email": "soumen@cse.iitb.ac.in",
            "lab": "IRLab",
            "projects": "Knowledge Graph Construction, Social Network Analysis",
            "url": "https://www.cse.iitb.ac.in/~soumen/"
        }
    ],
    "IIT Delhi": [
        {
            "name": "Prof. Sumantra Dutta Roy",
            "department": "Computer Science",
            "research": ["Computer Vision", "Medical Imaging", "AI for Healthcare"],
            "email": "sumantra@cse.iitd.ac.in",
            "lab": "IVP Lab",
            "projects": "AI-based Diagnosis, Medical Image Analysis",
            "url": "https://www.cse.iitd.ac.in/~sumantra/"
        },
        {
            "name": "Prof. Mausam",
            "department": "Computer Science",
            "research": ["NLP", "Reinforcement Learning", "AI Planning"],
            "email": "mausam@cse.iitd.ac.in",
            "lab": "MALL Lab",
            "projects": "Open Information Extraction, Planning Algorithms",
            "url": "https://www.cse.iitd.ac.in/~mausam/"
        }
    ],
    "IISc Bangalore": [
        {
            "name": "Prof. Chiranjib Bhattacharyya",
            "department": "Computer Science",
            "research": ["Optimization", "Machine Learning", "Large Scale Learning"],
            "email": "chiru@iisc.ac.in",
            "lab": "DEP Lab",
            "projects": "Optimization Algorithms, Scalable ML Systems",
            "url": "https://www.csa.iisc.ac.in/~chiru/"
        },
        {
            "name": "Prof. Vinod Ganapathy",
            "department": "Computer Science",
            "research": ["Systems Security", "Operating Systems", "Computer Architecture"],
            "email": "vinodg@iisc.ac.in",
            "lab": "OS Lab",
            "projects": "Secure Systems, Hardware Security",
            "url": "https://www.csa.iisc.ac.in/~vinodg/"
        }
    ],
    "NIT Trichy": [
        {
            "name": "Prof. B. Annappa",
            "department": "Computer Science",
            "research": ["Distributed Systems", "Cloud Computing", "IoT"],
            "email": "annappa@nitt.edu",
            "lab": "CSED",
            "projects": "Edge Computing, Distributed ML",
            "url": "https://www.nitt.edu/"
        }
    ],
    "VIT Vellore": [
        {
            "name": "Prof. S. Sivasathya",
            "department": "School of Computer Science",
            "research": ["Data Mining", "Bioinformatics", "Cloud Computing"],
            "email": "sivasathya@vit.ac.in",
            "lab": "SCOPE",
            "projects": "Healthcare Analytics, Cloud Security",
            "url": "https://vit.ac.in/"
        }
    ]
}

# ==================== INTERNSHIP DATABASE ====================

def get_internship_opportunities():
    """Latest internships from top institutes"""
    internships = [
        {
            "id": "INT001",
            "title": "Summer Research Internship - Machine Learning",
            "institute": "IIT Bombay",
            "professor": "Prof. Ganesh Ramakrishnan",
            "research_area": ["Deep Learning", "NLP", "LLMs"],
            "duration": "2-3 Months",
            "stipend": "₹15,000/month",
            "location": "Mumbai/Remote",
            "deadline": (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d"),
            "eligibility": "BTech/MTech students",
            "apply_link": "https://www.cse.iitb.ac.in/research/internships",
            "type": "Research Internship",
            "mode": "Hybrid"
        },
        {
            "id": "INT002",
            "title": "Computer Vision Research Intern",
            "institute": "IIT Delhi",
            "professor": "Prof. Sumantra Dutta Roy",
            "research_area": ["Medical Imaging", "Computer Vision", "AI Healthcare"],
            "duration": "6 Months",
            "stipend": "₹20,000/month",
            "location": "Delhi",
            "deadline": (datetime.now() + timedelta(days=20)).strftime("%Y-%m-%d"),
            "eligibility": "3rd/4th year BTech or MTech",
            "apply_link": "https://www.cse.iitd.ac.in/research/",
            "type": "Research Internship",
            "mode": "On-site"
        },
        {
            "id": "INT003",
            "title": "Systems Security Intern",
            "institute": "IISc Bangalore",
            "professor": "Prof. Vinod Ganapathy",
            "research_area": ["Systems Security", "OS Security", "Hardware Security"],
            "duration": "3-6 Months",
            "stipend": "₹25,000/month",
            "location": "Bangalore",
            "deadline": (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d"),
            "eligibility": "Computer Science students",
            "apply_link": "https://www.csa.iisc.ac.in/research/",
            "type": "Research Internship",
            "mode": "On-site"
        },
        {
            "id": "INT004",
            "title": "Summer Intern - Data Science",
            "institute": "VIT Vellore",
            "professor": "Prof. S. Sivasathya",
            "research_area": ["Data Mining", "Healthcare Analytics"],
            "duration": "2 Months",
            "stipend": "₹10,000/month",
            "location": "Vellore",
            "deadline": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
            "eligibility": "All years eligible",
            "apply_link": "https://vit.ac.in/research",
            "type": "Summer Internship",
            "mode": "On-site"
        },
        {
            "id": "INT005",
            "title": "Global Remote Intern - AI/ML",
            "institute": "Remote - Global",
            "professor": "Various",
            "research_area": ["Machine Learning", "Data Science", "GenAI"],
            "duration": "3-6 Months",
            "stipend": "$1000-3000/month",
            "location": "Remote (Worldwide)",
            "deadline": "Rolling Basis",
            "eligibility": "Global students",
            "apply_link": "https://research.google.com/",
            "type": "Global Remote Internship",
            "mode": "Remote"
        }
    ]
    return internships

# ==================== GLOBAL OPPORTUNITIES ====================

def get_global_opportunities():
    """Remote and global job/internship opportunities"""
    return [
        {
            "id": "GLOB001",
            "title": "Machine Learning Engineer Intern",
            "company": "OpenAI",
            "location": "Remote (US Timezone)",
            "type": "Internship",
            "mode": "Remote",
            "region": "USA",
            "salary": "$8,000/month",
            "requirements": ["Python", "PyTorch", "LLMs", "English Proficiency"],
            "apply_link": "https://openai.com/careers",
            "deadline": "Rolling"
        },
        {
            "id": "GLOB002",
            "title": "Data Scientist - Remote",
            "company": "Stripe",
            "location": "Remote (Global)",
            "type": "Full-time",
            "mode": "Remote",
            "region": "Global",
            "salary": "$120k-180k/year",
            "requirements": ["SQL", "Python", "Statistics", "5+ years exp"],
            "apply_link": "https://stripe.com/jobs",
            "deadline": "Open"
        },
        {
            "id": "GLOB003",
            "title": "AI Research Intern",
            "company": "DeepMind",
            "location": "London/Remote",
            "type": "Internship",
            "mode": "Hybrid",
            "region": "UK",
            "salary": "£4,000/month",
            "requirements": ["Deep Learning", "Research Papers", "Python"],
            "apply_link": "https://deepmind.com/careers",
            "deadline": "Nov 30, 2024"
        },
        {
            "id": "GLOB004",
            "title": "Software Engineer (AI/ML)",
            "company": "Tesla",
            "location": "Palo Alto, CA (Relocation Support)",
            "type": "Full-time",
            "mode": "On-site",
            "region": "USA",
            "salary": "$150k-220k/year",
            "requirements": ["C++", "Python", "Autonomous Systems"],
            "apply_link": "https://www.tesla.com/careers",
            "deadline": "Open"
        }
    ]

# ==================== COLD EMAIL GENERATOR ====================

def generate_professor_cold_email(professor, student_info, research_interest):
    """Generate personalized 10/10 cold email"""
    
    prof_name = professor.get('name', '')
    research_areas = professor.get('research', [])
    projects = professor.get('projects', '')
    lab = professor.get('lab', '')
    institute = professor.get('institute', '')
    
    # Match research interest with professor's areas
    matching_research = [r for r in research_areas if any(word in r.lower() for word in research_interest.lower().split())]
    research_mention = matching_research[0] if matching_research else research_areas[0] if research_areas else 'your work'
    
    email = f"""Subject: Research Internship Application - {research_mention} | {student_info.get('name', 'Student')}

Dear {prof_name},

I hope this email finds you well. My name is {student_info.get('name', 'Anil Pachar')}, and I am currently pursuing {student_info.get('degree', 'BTech')} in {student_info.get('branch', 'Computer Science')} at {student_info.get('university', 'NIT')}.

I am writing to express my strong interest in joining your research group at {lab}, {institute} as a summer research intern. I have been closely following your work on {projects}, particularly your recent contributions to {research_mention}. The approach you have taken toward {research_areas[1] if len(research_areas) > 1 else research_areas[0]} aligns perfectly with my research interests and career aspirations.

My background includes:
• Strong foundation in {', '.join(student_info.get('skills', ['Python', 'Machine Learning'])[:3])}
• Experience with {student_info.get('project_tech', 'Deep Learning frameworks and research methodologies')}
• {student_info.get('achievement', 'Published paper/Project experience')}

Specifically, I am fascinated by your work on {projects.split(',')[0] if projects else research_areas[0]} because [brief reason connecting to student's interest]. I believe my skills in {student_info.get('skills', ['Python'])[0]} would allow me to contribute meaningfully to ongoing projects in your lab.

I have attached my CV and a brief project portfolio for your review. I would be grateful for the opportunity to discuss potential research opportunities in your group and how I might contribute to your team's ongoing work.

Would it be possible to schedule a brief call or meeting to discuss this further? I am flexible with timing and can adjust to your schedule.

Thank you for your time and consideration. I look forward to hearing from you.

Best regards,
{student_info.get('name', 'Anil Pachar')}
{student_info.get('email', 'anil.pachar@email.com')}
{student_info.get('phone', '+91-XXXXXXXXXX')}
LinkedIn: {student_info.get('linkedin', 'linkedin.com/in/anil-pachar')}

Attachments:
1. CV_{student_info.get('name', 'Anil').replace(' ', '_')}.pdf
2. Project_Portfolio.pdf
"""
    return email

def generate_linkedin_connection_request(professor):
    """Generate LinkedIn connection request"""
    return f"""Hi {professor.get('name', '').split()[-1]}, I am Anil Pachar, a Computer Science student passionate about {professor.get('research', ['AI'])[0]}. I have been following your work on {professor.get('projects', 'research')} and would love to connect and learn from your expertise. Thank you!"""

# ==================== JOB DATA GENERATOR ====================

def generate_jobs():
    """Generate realistic job listings"""
    companies = ['Google', 'Microsoft', 'Amazon', 'Meta', 'Netflix', 'Adobe', 
                'Salesforce', 'Uber', 'Airbnb', 'LinkedIn', 'Twitter', 'Spotify',
                'Flipkart', 'Razorpay', 'Freshworks', 'Zomato', 'Swiggy', 'Ola']
    
    roles = ['Machine Learning Engineer', 'Data Scientist', 'AI Engineer', 
             'Software Engineer', 'Data Analyst', 'Gen AI Specialist']
    
    jobs = []
    for i in range(20):
        job = {
            'id': f"JOB{hashlib.md5(str(i).encode()).hexdigest()[:6].upper()}",
            'title': random.choice(roles),
            'company': random.choice(companies),
            'location': random.choice(['Remote', 'Bangalore', 'Hyderabad', 'Pune', 'Mumbai']),
            'type': random.choice(['Full-time', 'Contract']),
            'mode': random.choice(['Remote', 'Hybrid', 'On-site']),
            'region': 'India',
            'experience': f"{random.randint(1, 5)} years",
            'salary': f"₹{random.randint(10, 50)} LPA",
            'description': f"Looking for skilled professional with expertise in ML, Python, and Cloud.",
            'skills': ['Python', 'ML', 'AWS', 'SQL'],
            'match': random.randint(60, 98),
            'posted': random.randint(1, 7),
            'apply_link': f"https://careers.{random.choice(['google','amazon','microsoft'])}.com/apply/{i}"
        }
        jobs.append(job)
    return jobs

# ==================== AUTO-APPLY SYSTEM ====================

class ApplicationManager:
    def __init__(self):
        self.user = st.session_state
        
    def create_application_package(self, opportunity):
        """Create complete application package"""
        if not self.user['resume_text']:
            return None
        
        score, matched, missing = calculate_match_score(
            self.user['resume_text'], 
            opportunity.get('description', '')
        )
        
        tailored_resume = f"""PROFESSIONAL SUMMARY:
Results-driven professional with expertise in {', '.join(self.user['skills'][:4])}.

CORE SKILLS:
{', '.join(self.user['skills'][:8])}

EXPERIENCE:
Relevant experience in {', '.join(matched[:3]) if matched else 'modern technologies'}.
Additional capabilities: {', '.join(missing[:3]) if missing else 'Continuous learner'}

Generated for: {opportunity.get('title', 'Position')} at {opportunity.get('company', opportunity.get('institute', 'Organization'))}
"""
        
        cover_letter = f"""Dear Hiring Manager,

I am excited to apply for the {opportunity.get('title', 'Position')} role at {opportunity.get('company', opportunity.get('institute', 'your organization'))}.

With skills in {', '.join(self.user['skills'][:3])}, I am confident in my ability to contribute effectively.

Best regards,
{self.user['user_info']['name']}
"""
        
        return {
            'resume': tailored_resume,
            'cover_letter': cover_letter,
            'match_score': score,
            'missing_skills': missing
        }
    
    def auto_apply(self, opportunity):
        """Simulate auto-apply"""
        package = self.create_application_package(opportunity)
        if not package:
            return False, "Resume not uploaded"
        
        application = {
            'id': opportunity.get('id'),
            'title': opportunity.get('title'),
            'organization': opportunity.get('company', opportunity.get('institute', 'Unknown')),
            'date': datetime.now(),
            'status': 'Applied via Auto-Apply',
            'package': package,
            'type': 'Job' if 'company' in opportunity else 'Internship'
        }
        
        if opportunity.get('company'):
            self.user['applied_jobs'].append(application)
        else:
            self.user['applied_internships'].append(application)
        
        return True, "Application submitted successfully!"

# ==================== UI COMPONENTS ====================

def render_resume_upload():
    st.header("📄 Resume Upload & Profile Setup")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Upload Resume")
        file = st.file_uploader("Choose PDF or Image", type=['pdf', 'png', 'jpg', 'jpeg'])
        
        if file:
            with st.spinner("Processing..."):
                if file.type == "application/pdf":
                    text = extract_pdf_text(file)
                else:
                    text = extract_image_text(file)
                
                if "Error" not in text:
                    st.session_state.resume_text = text
                    st.session_state.skills = extract_skills(text)
                    st.success(f"Extracted {len(text)} characters")
                else:
                    st.error(text)
    
    with col2:
        st.subheader("Manual Entry / Edit")
        text = st.text_area("Paste or edit resume", value=st.session_state.resume_text, height=250)
        if st.button("Update Resume"):
            st.session_state.resume_text = text
            st.session_state.skills = extract_skills(text)
            st.success("Updated!")
    
    # Profile Info
    st.markdown("---")
    st.subheader("Personal Information for Applications")
    
    with st.form("user_info"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.session_state.user_info['name'] = st.text_input("Full Name", 
                value=st.session_state.user_info.get('name', 'Anil Pachar'))
            st.session_state.user_info['email'] = st.text_input("Email")
        with col2:
            st.session_state.user_info['phone'] = st.text_input("Phone")
            st.session_state.user_info['linkedin'] = st.text_input("LinkedIn URL")
        with col3:
            st.session_state.user_info['github'] = st.text_input("GitHub")
            st.session_state.user_info['degree'] = st.text_input("Degree (e.g., BTech CS)", 
                value="BTech Computer Science")
        
        st.form_submit_button("Save Profile")

def render_job_board():
    st.header("💼 Job Board & Internships")
    
    # Filters
    st.subheader("Filters")
    fcol1, fcol2, fcol3, fcol4 = st.columns(4)
    
    with fcol1:
        opp_type = st.selectbox("Opportunity Type", 
                               ["All", "Jobs Only", "Internships Only", "Research Internships"])
    with fcol2:
        work_mode = st.selectbox("Work Mode", 
                                ["All", "Remote", "Hybrid", "On-site"])
    with fcol3:
        region = st.selectbox("Region", 
                             ["All", "India", "USA", "Europe", "Global Remote"])
    with fcol4:
        institute = st.selectbox("Institute (for internships)", 
                                ["All", "IIT", "NIT", "IIIT", "IISc", "VIT", "Global"])
    
    # Combine all opportunities
    all_opportunities = []
    
    # Add jobs
    if opp_type in ["All", "Jobs Only"]:
        jobs = generate_jobs()
        for job in jobs:
            if (work_mode == "All" or job.get('mode') == work_mode) and \
               (region == "All" or job.get('region') == region or 
                (region == "India" and job.get('region') == 'India')):
                all_opportunities.append({**job, 'category': 'Job'})
    
    # Add internships
    if opp_type in ["All", "Internships Only", "Research Internships"]:
        internships = get_internship_opportunities()
        for intern in internships:
            if (work_mode == "All" or intern.get('mode') == work_mode) and \
               (institute == "All" or institute in intern.get('institute', '')):
                all_opportunities.append({**intern, 'category': 'Internship'})
    
    # Add global opportunities
    if region in ["All", "USA", "Europe", "Global Remote"]:
        global_opps = get_global_opportunities()
        for opp in global_opps:
            if (work_mode == "All" or opp.get('mode') == work_mode) and \
               (region == "All" or opp.get('region') == region or 
                (region == "Global Remote" and opp.get('mode') == 'Remote')):
                all_opportunities.append({**opp, 'category': 'Global'})
    
    # Display
    st.markdown(f"Showing {len(all_opportunities)} opportunities")
    
    app_manager = ApplicationManager()
    
    for opp in all_opportunities:
        is_internship = opp.get('category') == 'Internship'
        card_class = "internship-card" if is_internship else "job-card"
        
        with st.container():
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                title_icon = "🎓" if is_internship else "💼"
                st.markdown(f"### {title_icon} {opp.get('title')}")
                
                org = opp.get('company', opp.get('institute', 'Unknown'))
                st.markdown(f"**{org}**")
                
                loc = opp.get('location', 'Not specified')
                mode = opp.get('mode', 'Not specified')
                st.caption(f"📍 {loc} | 🏢 {mode} | 📋 {opp.get('type', 'Full-time')}")
                
                if is_internship:
                    prof = opp.get('professor', '')
                    if prof:
                        st.caption(f"👨‍🏫 Professor: {prof}")
                    research = opp.get('research_area', [])
                    if research:
                        st.caption(f"🔬 Research: {', '.join(research[:2])}")
            
            with col2:
                match = opp.get('match', random.randint(60, 95))
                st.markdown(f"**{match}% Match**")
                
                if 'salary' in opp:
                    st.caption(f"💰 {opp['salary']}")
                elif 'stipend' in opp:
                    st.caption(f"💰 {opp['stipend']}")
                
                if 'deadline' in opp:
                    st.caption(f"⏰ Deadline: {opp['deadline']}")
            
            with col3:
                # Auto Apply Button
                if st.button("⚡ Auto Apply", key=f"auto_{opp.get('id')}"):
                    success, msg = app_manager.auto_apply(opp)
                    if success:
                        st.success(msg)
                        st.balloons()
                    else:
                        st.error(msg)
                
                # Manual Apply Button
                if st.button("🔗 Manual Apply", key=f"manual_{opp.get('id')}"):
                    apply_link = opp.get('apply_link', '#')
                    st.markdown(f"[Click here to apply]({apply_link})")
                    st.info("Opens in new tab")
                
                # Save/Alert
                if st.button("🔔 Alert Me", key=f"alert_{opp.get('id')}"):
                    st.session_state.alerts.append(opp)
                    st.success("Alert set!")
            
            st.markdown("---")

def render_professor_database():
    st.header("🎓 Professor Database & Research Internships")
    st.write("Connect with professors at top institutes for research internships")
    
    # Institute Selection
    selected_institute = st.selectbox("Select Institute", 
                                     list(PROFESSOR_DB.keys()) + ["All"])
    
    if selected_institute == "All":
        institutes_to_show = PROFESSOR_DB
    else:
        institutes_to_show = {selected_institute: PROFESSOR_DB.get(selected_institute, [])}
    
    # Student Info for Cold Email
    st.subheader("Your Information (for Cold Email Generation)")
    with st.form("student_info"):
        col1, col2 = st.columns(2)
        with col1:
            student_name = st.text_input("Your Name", value=st.session_state.user_info.get('name', ''))
            student_degree = st.text_input("Degree", value="BTech Computer Science")
        with col2:
            research_interest = st.text_area("Your Research Interest", 
                                           placeholder="e.g., Natural Language Processing, Computer Vision")
            project_experience = st.text_area("Project Experience", 
                                            placeholder="e.g., Built sentiment analysis model using BERT")
        
        submit = st.form_submit_button("Update Profile")
        if submit:
            st.session_state.user_info.update({
                'name': student_name,
                'degree': student_degree,
                'research_interest': research_interest,
                'project_experience': project_experience
            })
    
    # Display Professors
    for institute, professors in institutes_to_show.items():
        st.markdown(f"### 🏛️ {institute}")
        
        for prof in professors:
            with st.expander(f"👨‍🏫 {prof.get('name')} - {prof.get('department')}"):
                st.markdown(f"**Laboratory:** {prof.get('lab', 'N/A')}")
                st.markdown(f"**Email:** {prof.get('email', 'N/A')}")
                st.markdown(f"**Website:** [{prof.get('url', 'Link')}]")
                
                st.markdown("**Research Areas:**")
                for area in prof.get('research', []):
                    st.markdown(f'<span class="research-area">{area}</span>', 
                               unsafe_allow_html=True)
                
                st.markdown(f"**Current Projects:** {prof.get('projects', 'N/A')}")
                
                # Generate Cold Email
                st.markdown("---")
                st.subheader("Cold Email Tools")
                
                if st.button(f"Generate Cold Email for {prof.get('name').split()[1]}", 
                            key=f"email_{prof.get('name')}"):
                    
                    student_info = {
                        'name': st.session_state.user_info.get('name', 'Student'),
                        'email': st.session_state.user_info.get('email', ''),
                        'degree': st.session_state.user_info.get('degree', 'BTech'),
                        'skills': st.session_state.skills,
                        'research_interest': research_interest or prof.get('research', [''])[0],
                        'project_tech': project_experience or 'Research experience',
                        'university': 'NIT'
                    }
                    
                    email = generate_professor_cold_email(prof, student_info, research_interest)
                    
                    st.text_area("Cold Email Template:", email, height=400)
                    
                    st.download_button("Download Email Template", email, 
                                      f"Cold_Email_{prof.get('name').replace(' ', '_')}.txt")
                    
                    # LinkedIn Message
                    linkedin_msg = generate_linkedin_connection_request(prof)
                    st.info(f"**LinkedIn Connection Request:**\n{linkedin_msg}")
                
                # Direct Application
                st.markdown("---")
                st.markdown(f"[🔗 Visit {institute} Careers Page](https://www.google.com/search?q={institute.replace(' ', '+')}+research+internships)")

def render_interview_prep():
    st.header("🎤 Interview Preparation Center")
    st.write("Comprehensive interview preparation for jobs and internships")
    
    tab1, tab2, tab3 = st.tabs(["Company Specific", "Role Based", "HR & Behavioral"])
    
    with tab1:
        company = st.selectbox("Select Company", 
                              ["Google", "Amazon", "Microsoft", "Meta", "Apple", "Netflix", "Startups"])
        
        if company == "Google":
            st.markdown("""
            **Google Interview Process:**
            1. **Online Assessment** - Coding + Workstyle
            2. **Phone Screen** - Technical (1 hour)
            3. **On-site/Virtual** - 4-5 rounds (Coding, System Design, Behavioral)
            
            **Key Topics:**
            - Data Structures & Algorithms
            - System Design (for SDE II+)
            - Googliness (Cultural fit)
            """)
            
            st.subheader("Sample Questions:")
            questions = [
                "Implement an LRU Cache",
                "Design a URL shortener",
                "Find median in data stream",
                "Tell me about a time you showed leadership"
            ]
            for q in questions:
                with st.expander(q):
                    st.write("**Approach:** Think aloud, discuss trade-offs, write clean code")
        
        elif company == "Amazon":
            st.markdown("""
            **Amazon LP (Leadership Principles) Focus:**
            Prepare 2-3 stories for each principle using STAR method.
            
            **Key Principles:** Customer Obsession, Ownership, Invent & Simplify, Dive Deep
            """)
            
            st.subheader("Sample LP Questions:")
            questions = [
                "Tell me about a time you had a conflict with a teammate",
                "Give an example of going above and beyond for a customer",
                "Tell me about a time you failed and what you learned"
            ]
            for q in questions:
                with st.expander(q):
                    st.write("**Format:** Situation → Task → Action → Result")
                    st.write("**Tip:** Use metrics and specific details")
    
    with tab2:
        role = st.selectbox("Select Role", 
                           ["Machine Learning Engineer", "Data Scientist", "Software Engineer", 
                            "Research Intern", "Gen AI Engineer"])
        
        if role == "Machine Learning Engineer":
            st.subheader("Technical Topics:")
            topics = ["ML System Design", "Model Deployment", "Feature Engineering", 
                     "Bias-Variance Tradeoff", "Gradient Descent Variants"]
            for topic in topics:
                st.markdown(f"- {topic}")
            
            st.subheader("System Design for ML:")
            st.write("Design a recommendation system, fraud detection, or search ranking system")
    
    with tab3:
        st.markdown("**Common HR Questions:**")
        questions = [
            "Tell me about yourself",
            "Why do you want to join our company?",
            "What are your salary expectations?",
            "Where do you see yourself in 5 years?"
        ]
        for q in questions:
            with st.expander(q):
                st.write("**Framework:** Keep it professional, connect to company values, show growth mindset")

def render_applications():
    st.header("📊 Application Dashboard")
    
    # Summary
    total_jobs = len(st.session_state.applied_jobs)
    total_internships = len(st.session_state.applied_internships)
    total_alerts = len(st.session_state.alerts)
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Job Applications", total_jobs)
    with c2:
        st.metric("Internship Applications", total_internships)
    with c3:
        st.metric("Total Applied", total_jobs + total_internships)
    with c4:
        st.metric("Active Alerts", total_alerts)
    
    # Applications List
    st.markdown("---")
    tab1, tab2 = st.tabs(["Job Applications", "Internship Applications"])
    
    with tab1:
        if not st.session_state.applied_jobs:
            st.info("No job applications yet. Visit the Job Board to apply!")
        else:
            for app in reversed(st.session_state.applied_jobs):
                with st.expander(f"{app.get('title')} at {app.get('organization')}"):
                    st.write(f"Applied: {app.get('date').strftime('%Y-%m-%d %H:%M')}")
                    st.write(f"Status: {app.get('status')}")
                    if app.get('package'):
                        st.write(f"Match Score: {app['package'].get('match_score', 0):.0f}%")
    
    with tab2:
        if not st.session_state.applied_internships:
            st.info("No internship applications yet.")
        else:
            for app in reversed(st.session_state.applied_internships):
                with st.expander(f"{app.get('title')} at {app.get('organization')}"):
                    st.write(f"Applied: {app.get('date').strftime('%Y-%m-%d %H:%M')}")
                    st.write(f"Type: Research Internship")
                    st.write(f"Status: {app.get('status')}")

# ==================== MAIN ====================

def main():
    st.markdown('<div class="main-header">Ultimate Job Tracker</div>', 
                unsafe_allow_html=True)
    st.caption("Professional Job Search & Research Internship Platform")
    
    # Alert Banner
    if st.session_state.alerts:
        st.markdown(f'<div class="alert-banner">🔔 You have {len(st.session_state.alerts)} active alerts set!</div>', 
                   unsafe_allow_html=True)
    
    # Navigation
    with st.sidebar:
        st.title("Navigation")
        page = st.radio("Go to", [
            "📄 Resume & Profile",
            "💼 Jobs & Internships",
            "🎓 Professor Database",
            "🎤 Interview Prep",
            "📊 My Applications"
        ])
        
        st.markdown("---")
        st.subheader("Quick Stats")
        total = len(st.session_state.applied_jobs) + len(st.session_state.applied_internships)
        st.write(f"Total Applications: {total}")
        st.write(f"Skills Detected: {len(st.session_state.skills)}")
        
        if st.session_state.skills:
            st.markdown("**Top Skills:**")
            for skill in st.session_state.skills[:5]:
                st.markdown(f"- {skill}")
    
    # Routing
    if "Resume & Profile" in page:
        render_resume_upload()
    elif "Jobs & Internships" in page:
        render_job_board()
    elif "Professor Database" in page:
        render_professor_database()
    elif "Interview Prep" in page:
        render_interview_prep()
    elif "My Applications" in page:
        render_applications()

if __name__ == "__main__":
    main()

