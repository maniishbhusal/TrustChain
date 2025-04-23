import PyPDF2
import re
import io
from django.conf import settings
import openai

class ResumeParser:
    def extract_text_from_pdf(self, pdf_file):
        """Extract text content from PDF file"""
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
        
    def extract_skills_using_ai(self, text):
        """Use AI to extract skills from resume text"""
        openai.api_key = settings.OPENAI_API_KEY
        
        prompt = f"""
        Extract all technical skills, programming languages, frameworks, and technologies 
        mentioned in this resume. Format the output as a JSON list of skills.
        
        Resume text:
        {text[:3000]}  # Limit text length to avoid token limits
        
        Return ONLY a JSON array of skills like: ["Python", "Django", "React", "AWS"]
        """
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a skill extraction assistant that outputs only JSON."},
                    {"role": "user", "content": prompt}
                ]
            )
            skills_text = response.choices[0].message.content.strip()
            
            # Clean up the response to ensure it's valid JSON
            skills_text = skills_text.replace("```json", "").replace("```", "").strip()
            skills = []
            
            try:
                skills = eval(skills_text)  # This is safer than json.loads as it can handle various formats
                if not isinstance(skills, list):
                    skills = []
            except:
                print("Error parsing AI response to JSON")
                
            return skills
        except Exception as e:
            print(f"Error using OpenAI API: {e}")
            return []
    
    def parse_resume(self, pdf_file):
        """Parse resume file and extract skills"""
        text = self.extract_text_from_pdf(pdf_file)
        skills = self.extract_skills_using_ai(text)
        return {
            'text': text[:1000],  # Just store a preview of the text
            'skills': skills
        }