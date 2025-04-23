import openai
from django.conf import settings
import hashlib
import json

class SkillAnalyzer:
    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        openai.api_key = self.openai_api_key
    
    def analyze_github_skills(self, github_data):
        """Use AI to analyze GitHub data and extract skills"""
        # Prepare a condensed version of the GitHub data to fit within token limits
        condensed_data = {
            'username': github_data['username'],
            'repos': []
        }
        
        for repo in github_data['repos']:
            # Only include essential information
            condensed_repo = {
                'name': repo['name'],
                'description': repo['description'],
                'languages': repo['languages'],
                'topics': repo['topics'],
                'stars': repo['stars'],
                'readme_snippet': repo['readme'][:500] if repo['readme'] else ""
            }
            condensed_data['repos'].append(condensed_repo)
        
        prompt = f"""
        Based on this GitHub profile data, identify the technical skills demonstrated:
        {json.dumps(condensed_data, indent=2)}
        
        Please analyze the repositories, languages used, topics, and README content to determine:
        1. Programming languages the user is proficient in
        2. Frameworks and libraries they have experience with
        3. Tools and technologies they work with
        
        Return ONLY a JSON array of skills like: ["Python", "Django", "React", "AWS"]
        """
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a skill analysis assistant that outputs only JSON."},
                    {"role": "user", "content": prompt}
                ]
            )
            skills_text = response.choices[0].message.content.strip()
            
            # Clean up the response to ensure it's valid JSON
            skills_text = skills_text.replace("```json", "").replace("```", "").strip()
            skills = []
            
            try:
                skills = eval(skills_text)
                if not isinstance(skills, list):
                    skills = []
            except:
                print("Error parsing AI response to JSON")
                
            return skills
        except Exception as e:
            print(f"Error using OpenAI API: {e}")
            return []
    
    def verify_skills(self, resume_skills, github_skills):
        """Compare skills from resume with skills from GitHub"""
        # Convert to lowercase for case-insensitive comparison
        resume_skills_lower = [skill.lower() for skill in resume_skills]
        github_skills_lower = [skill.lower() for skill in github_skills]
        
        # Find common skills
        common_skills = list(set(resume_skills_lower) & set(github_skills_lower))
        
        # Skills in resume but not found in GitHub
        unverified_skills = [skill for skill in resume_skills if skill.lower() not in github_skills_lower]
        
        # Skills in GitHub but not mentioned in resume
        additional_skills = [skill for skill in github_skills if skill.lower() not in resume_skills_lower]
        
        return {
            'verified_skills': common_skills,
            'unverified_skills': unverified_skills,
            'additional_skills': additional_skills,
            'verification_percentage': len(common_skills) / len(resume_skills) * 100 if resume_skills else 0
        }
    
    def generate_verification_hash(self, github_username, verified_skills):
        """Generate a hash of verified skills that can be stored on blockchain"""
        skills_string = ",".join(sorted(verified_skills))
        data_to_hash = f"{github_username}:{skills_string}:{settings.SECRET_KEY}"
        hash_object = hashlib.sha256(data_to_hash.encode())
        return hash_object.hexdigest()