import openai
from django.conf import settings
import hashlib
import json
from django.core.cache import cache


class SkillAnalyzer:
    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        openai.api_key = self.openai_api_key

    def _get_cache_key(self, method_name, *args):
        """Generate a cache key based on method name and arguments"""
        key_parts = [method_name]
        for arg in args:
            if isinstance(arg, (list, dict)):
                key_parts.append(hashlib.md5(json.dumps(
                    arg, sort_keys=True).encode()).hexdigest())
            else:
                key_parts.append(str(arg))
        key = "_".join(key_parts)
        # Create a hash for long keys
        if len(key) > 250:
            key = f"skill_{hashlib.md5(key.encode()).hexdigest()}"
        return key

    def analyze_github_skills(self, github_data):
        """Use AI to analyze GitHub data and extract skills with caching"""
        # Create cache key based on essential GitHub data
        cache_key = self._get_cache_key("github_skills_analysis",
                                        github_data['username'],
                                        [repo['name'] for repo in github_data['repos']])
        cached_skills = cache.get(cache_key)

        if cached_skills is not None:
            print(f"Cache hit: {cache_key}")
            return cached_skills

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
            skills_text = skills_text.replace(
                "```json", "").replace("```", "").strip()
            skills = []

            try:
                skills = eval(skills_text)
                if not isinstance(skills, list):
                    skills = []

                # Cache the result
                cache.set(cache_key, skills,
                          settings.VERIFICATION_CACHE_TIMEOUT)
                return skills
            except:
                print("Error parsing AI response to JSON")
                return []
        except Exception as e:
            print(f"Error using OpenAI API: {e}")
            return []

    def verify_skills_with_llm(self, resume_skills, github_skills):
        """Use LLM to intelligently compare resume skills with GitHub skills, with caching"""
        # Create cache key based on resume skills and GitHub skills
        cache_key = self._get_cache_key(
            "verify_skills_llm", resume_skills, github_skills)
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            print(f"Cache hit: {cache_key}")
            return cached_result

        prompt = f"""
        I need to compare skills claimed in a resume with skills demonstrated on GitHub.

Resume skills: {json.dumps(resume_skills)}
GitHub skills: {json.dumps(github_skills)}

Your task:
You are a senior software engineer and recruiter. Cross-analyze resume skills with GitHub activity. Determine which skills are actually practiced and how strongly they are demonstrated.

Instructions:
1. Match resume skills with GitHub skills. Consider equivalent or related terms (e.g., "React" = "React.js", "Express.js" = "Express", "Tailwind CSS" ⊂ "CSS").
2. List which skills from the resume are verified by GitHub.
3. Identify resume skills that are not verified on GitHub.
4. Highlight additional relevant skills found on GitHub but not in the resume.
5. Calculate a verification percentage = (verified skills / total resume skills) * 100.
6. Assign a `strength_per_skill` score for each resume skill (scale: 0-10) based on how well it is represented in GitHub repos (e.g., number of projects using it, README mentions, commits, repo structure).
7. In the `explanation`, explain your reasoning and give a final credibility score out of 10.

Return a JSON object with exactly these keys:
- verified_skills: array of verified skills (use the resume's original naming)
- unverified_skills: array of resume skills not verified from GitHub
- additional_skills: array of GitHub skills not in the resume
- verification_percentage: number between 0 and 100
- strength_per_skill: object where each key is a resume skill and value is a number (0-10)
- explanation: short summary with logic, findings, and an overall credibility score out of 10

        """

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a skill verification assistant that outputs JSON with reasoning."},
                    {"role": "user", "content": prompt}
                ]
            )
            result_text = response.choices[0].message.content.strip()

            # Clean up the response to ensure it's valid JSON
            result_text = result_text.replace(
                "```json", "").replace("```", "").strip()
            result = {}

            try:
                result = json.loads(result_text)
                # Ensure all required keys exist
                required_keys = ['verified_skills', 'unverified_skills',
                                 'additional_skills', 'verification_percentage', 'explanation']
                for key in required_keys:
                    if key not in result:
                        if key == 'explanation':
                            result[key] = "No explanation provided"
                        else:
                            result[key] = [] if 'skills' in key else 0

                # Cache the result
                cache.set(cache_key, result,
                          settings.VERIFICATION_CACHE_TIMEOUT)
                return result
            except Exception as e:
                print(f"Error parsing AI verification response: {e}")
                # Fallback to basic verification
                result = self.basic_skill_verification(
                    resume_skills, github_skills)
                return result
        except Exception as e:
            print(f"Error using OpenAI API for verification: {e}")
            # Fallback to basic verification
            return self.basic_skill_verification(resume_skills, github_skills)

    def basic_skill_verification(self, resume_skills, github_skills):
        """Basic fallback method for skill verification"""
        # Convert to lowercase for case-insensitive comparison
        resume_skills_lower = [skill.lower() for skill in resume_skills]
        github_skills_lower = [skill.lower() for skill in github_skills]

        # Find common skills (this is a simple approach as fallback)
        common_skills = list(set(resume_skills_lower) &
                             set(github_skills_lower))

        # Skills in resume but not found in GitHub
        unverified_skills = [
            skill for skill in resume_skills if skill.lower() not in github_skills_lower]

        # Skills in GitHub but not mentioned in resume
        additional_skills = [
            skill for skill in github_skills if skill.lower() not in resume_skills_lower]

        return {
            'verified_skills': common_skills,
            'unverified_skills': unverified_skills,
            'additional_skills': additional_skills,
            'verification_percentage': len(common_skills) / len(resume_skills) * 100 if resume_skills else 0,
            'explanation': "Basic comparison performed. This is a fallback method."
        }

    def generate_verification_hash(self, github_username, verified_skills):
        """Generate a hash of verified skills that can be stored on blockchain"""
        skills_string = ",".join(
            sorted([skill.lower() for skill in verified_skills]))
        data_to_hash = f"{github_username}:{skills_string}:{settings.SECRET_KEY}"
        hash_object = hashlib.sha256(data_to_hash.encode())
        return hash_object.hexdigest()
