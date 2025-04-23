import requests
import base64
from django.conf import settings
import json

class GitHubService:
    def __init__(self, username):
        self.username = username
        self.headers = {'Authorization': f'token {settings.GITHUB_TOKEN}'} if settings.GITHUB_TOKEN else {}
        
    def get_user_repos(self):
        """Get list of user's public repositories"""
        url = f"https://api.github.com/users/{self.username}/repos"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching repos: {response.status_code}")
            return []
            
    def get_repo_languages(self, repo_name):
        """Get languages used in a repository"""
        url = f"https://api.github.com/repos/{self.username}/{repo_name}/languages"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            return {}
            
    def get_repo_commits(self, repo_name, max_commits=10):
        """Get recent commits in a repository"""
        url = f"https://api.github.com/repos/{self.username}/{repo_name}/commits"
        params = {'per_page': max_commits}
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            return []
            
    def get_repo_readme(self, repo_name):
        """Get repository README content"""
        url = f"https://api.github.com/repos/{self.username}/{repo_name}/readme"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            content = response.json().get('content', '')
            if content:
                return base64.b64decode(content).decode('utf-8')
        return ""
        
    def get_repo_topics(self, repo_name):
        """Get repository topics/tags"""
        url = f"https://api.github.com/repos/{self.username}/{repo_name}/topics"
        # GitHub API requires a specific media type for this endpoint
        headers = self.headers.copy()
        headers['Accept'] = 'application/vnd.github.mercy-preview+json'
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json().get('names', [])
        else:
            return []
            
    def collect_repo_data(self, repo_name):
        """Collect all data for a single repository"""
        languages = self.get_repo_languages(repo_name)
        commits = self.get_repo_commits(repo_name)
        readme = self.get_repo_readme(repo_name)
        topics = self.get_repo_topics(repo_name)
        
        return {
            'name': repo_name,
            'languages': languages,
            'commits': commits,
            'readme': readme,
            'topics': topics
        }
        
    def get_all_github_data(self, max_repos=5):
        """Get all relevant GitHub data for the user"""
        repos = self.get_user_repos()
        all_data = {
            'username': self.username,
            'repos': []
        }
        
        # Only process a limited number of repos for performance
        for repo in repos[:max_repos]:
            repo_name = repo.get('name')
            repo_data = self.collect_repo_data(repo_name)
            # Add metadata from the repo listing
            repo_data.update({
                'description': repo.get('description'),
                'stars': repo.get('stargazers_count'),
                'forks': repo.get('forks_count'),
                'created_at': repo.get('created_at'),
                'updated_at': repo.get('updated_at')
            })
            all_data['repos'].append(repo_data)
            
        return all_data