import requests
import base64
from django.conf import settings
import json
import hashlib
from django.core.cache import cache
import re
from collections import Counter
import os
import tempfile
import subprocess
from git import Repo
import lizard  # You'll need to install this: pip install lizard

class GitHubService:
    def __init__(self, username):
        self.username = username
        self.headers = {'Authorization': f'token {settings.GITHUB_TOKEN}'} if settings.GITHUB_TOKEN else {}
        
    def _get_cache_key(self, method_name, *args):
        """Generate a cache key based on method name and arguments"""
        key_parts = [self.username, method_name]
        key_parts.extend([str(arg) for arg in args])
        key = "_".join(key_parts)
        # Create a hash for long keys
        if len(key) > 250:
            key = f"gh_{hashlib.md5(key.encode()).hexdigest()}"
        return key
        
    def get_user_repos(self):
        """Get list of user's public repositories with caching"""
        cache_key = self._get_cache_key("user_repos")
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            print(f"Cache hit: {cache_key}")
            return cached_data
            
        url = f"https://api.github.com/users/{self.username}/repos"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            data = response.json()
            cache.set(cache_key, data, settings.GITHUB_CACHE_TIMEOUT)
            return data
        else:
            print(f"Error fetching repos: {response.status_code}")
            return []
            
    def get_repo_languages(self, repo_name):
        """Get languages used in a repository with caching"""
        cache_key = self._get_cache_key("repo_languages", repo_name)
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            print(f"Cache hit: {cache_key}")
            return cached_data
            
        url = f"https://api.github.com/repos/{self.username}/{repo_name}/languages"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            data = response.json()
            cache.set(cache_key, data, settings.GITHUB_CACHE_TIMEOUT)
            return data
        else:
            return {}
            
    def get_repo_commits(self, repo_name, max_commits=10):
        """Get recent commits in a repository with caching"""
        cache_key = self._get_cache_key("repo_commits", repo_name, max_commits)
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            print(f"Cache hit: {cache_key}")
            return cached_data
            
        url = f"https://api.github.com/repos/{self.username}/{repo_name}/commits"
        params = {'per_page': max_commits}
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            cache.set(cache_key, data, settings.GITHUB_CACHE_TIMEOUT)
            return data
        else:
            return []
            
    def get_repo_readme(self, repo_name):
        """Get repository README content with caching"""
        cache_key = self._get_cache_key("repo_readme", repo_name)
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            print(f"Cache hit: {cache_key}")
            return cached_data
            
        url = f"https://api.github.com/repos/{self.username}/{repo_name}/readme"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            content = response.json().get('content', '')
            if content:
                readme = base64.b64decode(content).decode('utf-8')
                cache.set(cache_key, readme, settings.GITHUB_CACHE_TIMEOUT)
                return readme
        return ""
        
    def get_repo_topics(self, repo_name):
        """Get repository topics/tags with caching"""
        cache_key = self._get_cache_key("repo_topics", repo_name)
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            print(f"Cache hit: {cache_key}")
            return cached_data
            
        url = f"https://api.github.com/repos/{self.username}/{repo_name}/topics"
        # GitHub API requires a specific media type for this endpoint
        headers = self.headers.copy()
        headers['Accept'] = 'application/vnd.github.mercy-preview+json'
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json().get('names', [])
            cache.set(cache_key, data, settings.GITHUB_CACHE_TIMEOUT)
            return data
        else:
            return []

    # NEW CODE ANALYSIS METHODS START HERE
    
    def clone_repo(self, repo_name):
        """Clone a repository to a temporary directory for analysis"""
        cache_key = self._get_cache_key("repo_clone_path", repo_name)
        cached_path = cache.get(cache_key)
        
        if cached_path is not None and os.path.exists(cached_path):
            print(f"Cache hit: {cache_key}")
            return cached_path
            
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp(prefix=f"gh_{repo_name}_")
        
        try:
            clone_url = f"https://github.com/{self.username}/{repo_name}.git"
            Repo.clone_from(clone_url, temp_dir)
            
            # Cache the path (shorter timeout to avoid disk space issues)
            cache_timeout = getattr(settings, 'GITHUB_CLONE_CACHE_TIMEOUT', 60 * 30)  # Default 30 min
            cache.set(cache_key, temp_dir, cache_timeout)
            
            return temp_dir
        except Exception as e:
            print(f"Error cloning repository {repo_name}: {e}")
            return None
            
    def identify_libraries(self, repo_path):
        """Identify libraries and frameworks used in the repository"""
        cache_key = self._get_cache_key("repo_libraries", repo_path)
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            print(f"Cache hit: {cache_key}")
            return cached_data
            
        library_patterns = {
            'Python': {
                'import (.+?)($| as| #)': 1,
                'from (.+?) import': 1
            },
            'JavaScript': {
                'require\\([\'"](.+?)[\'"]\\)': 1,
                'import .+ from [\'"](.+?)[\'"]': 1,
                'import [\'"](.+?)[\'"]': 1
            }
        }
        
        libraries = Counter()
        file_count = 0
        
        for root, dirs, files in os.walk(repo_path):
            # Skip hidden directories and common non-source directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', 'env', '__pycache__']]
            
            for file in files:
                if file_count > 500:  # Limit analysis for large repos
                    break
                    
                ext = os.path.splitext(file)[1].lower()
                
                if ext == '.py':
                    lang = 'Python'
                elif ext in ['.js', '.jsx', '.ts', '.tsx']:
                    lang = 'JavaScript'
                else:
                    continue
                    
                file_count += 1
                
                if lang in library_patterns:
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            for pattern, group_idx in library_patterns[lang].items():
                                matches = re.finditer(pattern, content)
                                for match in matches:
                                    try:
                                        lib = match.group(group_idx).split('.')[0].strip()
                                        if lib and len(lib) < 50:  # Sanity check
                                            libraries[lib] += 1
                                    except:
                                        continue
                    except:
                        continue
        
        # Convert to dict for JSON serialization
        result = {lib: count for lib, count in libraries.most_common(20)}
        cache.set(cache_key, result, settings.GITHUB_CACHE_TIMEOUT)
        return result
            
    def analyze_code_complexity(self, repo_path):
        """Analyze code complexity using lizard"""
        cache_key = self._get_cache_key("repo_complexity", repo_path)
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            print(f"Cache hit: {cache_key}")
            return cached_data
            
        results = {
            'summary': {
                'avg_complexity': 0,
                'avg_nloc': 0,
                'total_functions': 0
            },
            'languages': {},
            'high_complexity_functions': []
        }
        
        try:
            # Find all code files
            code_extensions = ['.py', '.js', '.java', '.cpp', '.c', '.go', '.rb', '.php', '.ts', '.jsx', '.tsx']
            code_files = []
            
            for root, dirs, files in os.walk(repo_path):
                # Skip hidden directories and common non-source directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', 'env', '__pycache__']]
                
                for file in files:
                    if any(file.endswith(ext) for ext in code_extensions):
                        code_files.append(os.path.join(root, file))
                        
                if len(code_files) > 200:  # Limit for large repositories
                    break
            
            # Analyze files
            total_ccn = 0
            total_nloc = 0
            function_count = 0
            
            for file_path in code_files[:200]:  # Limit to 200 files
                try:
                    analysis = lizard.analyze_file(file_path)
                    
                    # Track language stats
                    rel_path = os.path.relpath(file_path, repo_path)
                    file_ext = os.path.splitext(file_path)[1][1:]  # Remove the dot
                    
                    if file_ext not in results['languages']:
                        results['languages'][file_ext] = {
                            'file_count': 0,
                            'function_count': 0,
                            'avg_complexity': 0
                        }
                    
                    results['languages'][file_ext]['file_count'] += 1
                    lang_func_count = len(analysis.function_list)
                    results['languages'][file_ext]['function_count'] += lang_func_count
                    
                    if lang_func_count > 0:
                        lang_total_ccn = sum(func.cyclomatic_complexity for func in analysis.function_list)
                        results['languages'][file_ext]['avg_complexity'] = round(
                            (results['languages'][file_ext]['avg_complexity'] * 
                             (results['languages'][file_ext]['function_count'] - lang_func_count) + 
                             lang_total_ccn) / results['languages'][file_ext]['function_count'], 2)
                    
                    # Track overall stats
                    for func in analysis.function_list:
                        total_ccn += func.cyclomatic_complexity
                        total_nloc += func.nloc
                        function_count += 1
                        
                        # Track complex functions
                        if func.cyclomatic_complexity > 10:  # High complexity threshold
                            results['high_complexity_functions'].append({
                                'name': func.name,
                                'file': rel_path,
                                'ccn': func.cyclomatic_complexity,
                                'nloc': func.nloc,
                                'params': func.parameter_count
                            })
                
                except Exception as e:
                    continue
            
            # Calculate overall averages
            if function_count > 0:
                results['summary']['avg_complexity'] = round(total_ccn / function_count, 2)
                results['summary']['avg_nloc'] = round(total_nloc / function_count, 2)
                results['summary']['total_functions'] = function_count
            
            # Sort high complexity functions
            results['high_complexity_functions'] = sorted(
                results['high_complexity_functions'], 
                key=lambda x: x['ccn'], 
                reverse=True
            )[:10]  # Keep only top 10
        
        except Exception as e:
            print(f"Error analyzing code complexity: {e}")
        
        cache.set(cache_key, results, settings.GITHUB_CACHE_TIMEOUT)
        return results
    
    def identify_coding_patterns(self, repo_path):
        """Identify coding patterns and practices"""
        cache_key = self._get_cache_key("repo_patterns", repo_path)
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            print(f"Cache hit: {cache_key}")
            return cached_data
            
        patterns = {
            'has_tests': False,
            'has_ci': False,
            'has_docs': False,
            'has_linter': False,
            'uses_oop': False,
            'uses_functional': False,
            'frameworks': []
        }
        
        try:
            # Check for tests
            test_dirs = ['test', 'tests', 'spec', 'specs', '__tests__']
            test_files = [f for f in os.listdir(repo_path) if any(f.startswith(prefix) for prefix in test_dirs) or 
                          any(f.endswith(suffix) for suffix in ['test.py', 'test.js', '_test.py', '_test.js', '.spec.js'])]
            
            patterns['has_tests'] = len(test_files) > 0
            
            # Check for CI
            ci_files = ['.travis.yml', '.gitlab-ci.yml', '.github/workflows', 'azure-pipelines.yml', 'Jenkinsfile']
            for ci_file in ci_files:
                if os.path.exists(os.path.join(repo_path, ci_file)):
                    patterns['has_ci'] = True
                    break
            
            # Check for docs
            doc_dirs = ['docs', 'doc', 'documentation', 'wiki']
            for doc_dir in doc_dirs:
                if os.path.exists(os.path.join(repo_path, doc_dir)):
                    patterns['has_docs'] = True
                    break
            
            # Check for linters
            linter_files = ['.eslintrc', '.pylintrc', 'flake8', '.flake8', 'mypy.ini', 'tslint.json', '.jshintrc']
            for linter_file in linter_files:
                if os.path.exists(os.path.join(repo_path, linter_file)):
                    patterns['has_linter'] = True
                    break
            
            # Check for OOP
            patterns['uses_oop'] = self._check_for_oop(repo_path)
            
            # Check for functional programming
            patterns['uses_functional'] = self._check_for_functional(repo_path)
            
            # Identify frameworks
            patterns['frameworks'] = self._identify_frameworks(repo_path)
            
        except Exception as e:
            print(f"Error identifying coding patterns: {e}")
            
        cache.set(cache_key, patterns, settings.GITHUB_CACHE_TIMEOUT)
        return patterns
    
    def _check_for_oop(self, repo_path):
        """Check if repository uses object-oriented programming"""
        class_patterns = {
            '.py': r'class\s+\w+(\(\w+\))?:',
            '.js': r'class\s+\w+(\s+extends\s+\w+)?(\s+implements\s+\w+)?\s*{',
            '.java': r'(public|private|protected)?\s+class\s+\w+(\s+extends\s+\w+)?(\s+implements\s+\w+)?\s*{'
        }
        
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', 'env', '__pycache__']]
            
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in class_patterns:
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if re.search(class_patterns[ext], content):
                                return True
                    except:
                        continue
        
        return False
    
    def _check_for_functional(self, repo_path):
        """Check if repository uses functional programming patterns"""
        functional_patterns = {
            '.py': [r'lambda\s+', r'map\(', r'filter\(', r'reduce\('],
            '.js': [r'=>', r'\.map\(', r'\.filter\(', r'\.reduce\(']
        }
        
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', 'env', '__pycache__']]
            
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in functional_patterns:
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            for pattern in functional_patterns[ext]:
                                if re.search(pattern, content):
                                    return True
                    except:
                        continue
        
        return False
    
    def _identify_frameworks(self, repo_path):
        """Identify common frameworks used in the project"""
        framework_indicators = {
            'django': ['settings.py', 'urls.py', 'wsgi.py', 'asgi.py'],
            'flask': ['app.py', 'Flask(__name__)', 'flask import'],
            'react': ['react', 'ReactDOM', 'jsx'],
            'angular': ['@angular', 'ngModule'],
            'vue': ['createApp', 'Vue.createApp', '.vue'],
            'express': ['express()', 'app.listen(', 'express.Router()'],
            'spring': ['@SpringBootApplication', '@RestController', 'SpringApplication'],
            'laravel': ['artisan', 'Illuminate\\'],
            'rails': ['config/routes.rb', 'app/controllers']
        }
        
        detected_frameworks = []
        
        # Check package.json for JS frameworks
        package_json_path = os.path.join(repo_path, 'package.json')
        if os.path.exists(package_json_path):
            try:
                with open(package_json_path, 'r') as f:
                    package_data = json.load(f)
                    dependencies = {**package_data.get('dependencies', {}), **package_data.get('devDependencies', {})}
                    
                    if 'react' in dependencies:
                        detected_frameworks.append('react')
                    if 'vue' in dependencies:
                        detected_frameworks.append('vue')
                    if 'angular' in dependencies or '@angular/core' in dependencies:
                        detected_frameworks.append('angular')
                    if 'express' in dependencies:
                        detected_frameworks.append('express')
            except:
                pass
        
        # Check requirements.txt for Python frameworks
        requirements_path = os.path.join(repo_path, 'requirements.txt')
        if os.path.exists(requirements_path):
            try:
                with open(requirements_path, 'r') as f:
                    content = f.read().lower()
                    if 'django' in content:
                        detected_frameworks.append('django')
                    if 'flask' in content:
                        detected_frameworks.append('flask')
            except:
                pass
        
        # Check for framework-specific files
        for framework, indicators in framework_indicators.items():
            if framework in detected_frameworks:
                continue
                
            for indicator in indicators:
                if indicator.endswith('.py') or indicator.endswith('.rb'):
                    # Check for specific files
                    indicator_found = False
                    for root, dirs, files in os.walk(repo_path):
                        if indicator in files:
                            detected_frameworks.append(framework)
                            indicator_found = True
                            break
                    if indicator_found:
                        break
                else:
                    # Check for code patterns
                    pattern_found = False
                    for root, dirs, files in os.walk(repo_path):
                        for file in files:
                            if file.endswith(('.js', '.py', '.php', '.java')):
                                try:
                                    with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as f:
                                        content = f.read()
                                        if indicator in content:
                                            detected_frameworks.append(framework)
                                            pattern_found = True
                                            break
                                except:
                                    continue
                        if pattern_found:
                            break
                    if pattern_found:
                        break
        
        return list(set(detected_frameworks))  # Remove duplicates
    
    def analyze_repo(self, repo_name):
        """Analyze a repository and provide comprehensive data"""
        cache_key = self._get_cache_key("repo_analysis", repo_name)
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            print(f"Cache hit: {cache_key}")
            return cached_data
            
        repo_path = self.clone_repo(repo_name)
        if not repo_path:
            return {
                'error': 'Failed to clone repository',
                'basic_info': self.collect_repo_data(repo_name)
            }
        
        # Gather different analysis components
        analysis_data = {
            'basic_info': self.collect_repo_data(repo_name),
            'libraries': self.identify_libraries(repo_path),
            'complexity': self.analyze_code_complexity(repo_path),
            'patterns': self.identify_coding_patterns(repo_path)
        }
        
        # Generate skill metrics
        skills = self._generate_skill_metrics(analysis_data)
        analysis_data['skills'] = skills
        
        cache.set(cache_key, analysis_data, settings.GITHUB_CACHE_TIMEOUT)
        return analysis_data
    
    def _generate_skill_metrics(self, analysis_data):
        """Generate a skill assessment based on analysis data"""
        skills = {
            'languages': {},
            'frameworks': [],
            'practices': {
                'testing': analysis_data['patterns']['has_tests'],
                'ci_cd': analysis_data['patterns']['has_ci'],
                'documentation': analysis_data['patterns']['has_docs'],
                'code_quality': analysis_data['patterns']['has_linter']
            },
            'paradigms': {
                'object_oriented': analysis_data['patterns']['uses_oop'],
                'functional': analysis_data['patterns']['uses_functional']
            },
            'code_metrics': {
                'complexity': analysis_data['complexity']['summary']['avg_complexity'],
                'function_size': analysis_data['complexity']['summary']['avg_nloc'],
                'function_count': analysis_data['complexity']['summary']['total_functions']
            }
        }
        
        # Process language data
        languages = analysis_data['basic_info']['languages']
        total_bytes = sum(languages.values()) if languages else 0
        
        if total_bytes > 0:
            for lang, bytes_count in languages.items():
                percentage = (bytes_count / total_bytes) * 100
                skills['languages'][lang] = {
                    'bytes': bytes_count,
                    'percentage': round(percentage, 2)
                }
        
        # Add frameworks
        skills['frameworks'] = analysis_data['patterns']['frameworks']
        
        # Add libraries used
        skills['libraries'] = list(analysis_data['libraries'].keys())[:10]
        
        return skills
    
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
        
    def get_all_github_data(self, max_repos=5, analyze=False):
        """Get all relevant GitHub data for the user with caching
        
        Parameters:
        - max_repos: Maximum number of repositories to fetch
        - analyze: Whether to perform code analysis (default: False)
        """
        cache_key = self._get_cache_key("all_github_data", max_repos, analyze)
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            print(f"Cache hit: {cache_key}")
            return cached_data
            
        repos = self.get_user_repos()
        all_data = {
            'username': self.username,
            'repos': []
        }
        
        # Sort repos by stars first
        repos = sorted(repos, key=lambda r: r.get('stargazers_count', 0), reverse=True)
        
        # Only process a limited number of repos for performance
        for repo in repos[:max_repos]:
            repo_name = repo.get('name')
            
            if analyze:
                # Use the new analysis functionality
                repo_data = self.analyze_repo(repo_name)
            else:
                # Use the original functionality
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
        
        cache.set(cache_key, all_data, settings.GITHUB_CACHE_TIMEOUT)    
        return all_data
    
    def generate_skills_summary(self, max_repos=5):
        """Generate a summary of skills based on repository analysis"""
        cache_key = self._get_cache_key("skills_summary", max_repos)
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            print(f"Cache hit: {cache_key}")
            return cached_data
            
        # Get detailed data from repositories
        github_data = self.get_all_github_data(max_repos=max_repos, analyze=True)
        
        # Aggregate skills across repositories
        all_languages = Counter()
        all_libraries = Counter()
        all_frameworks = []
        
        code_metrics = {
            'avg_complexity': [],
            'avg_function_size': [],
            'total_functions': 0
        }
        
        practices = {
            'testing': 0,
            'ci_cd': 0,
            'documentation': 0,
            'code_quality': 0,
            'oop': 0,
            'functional': 0
        }
        
        for repo in github_data['repos']:
            # Skip repos that couldn't be analyzed
            if 'error' in repo:
                continue
                
            # Aggregate languages
            if 'basic_info' in repo and 'languages' in repo['basic_info']:
                for lang, bytes_count in repo['basic_info']['languages'].items():
                    all_languages[lang] += bytes_count
            
            # Aggregate libraries
            if 'libraries' in repo:
                for lib, count in repo['libraries'].items():
                    all_libraries[lib] += count
            
            # Aggregate frameworks
            if 'patterns' in repo and 'frameworks' in repo['patterns']:
                all_frameworks.extend(repo['patterns']['frameworks'])
            
            # Aggregate code metrics
            if 'complexity' in repo and 'summary' in repo['complexity']:
                summary = repo['complexity']['summary']
                if summary['total_functions'] > 0:
                    code_metrics['avg_complexity'].append(summary['avg_complexity'])
                    code_metrics['avg_function_size'].append(summary['avg_nloc'])
                    code_metrics['total_functions'] += summary['total_functions']
            
            # Aggregate practices
            if 'patterns' in repo:
                patterns = repo['patterns']
                practices['testing'] += 1 if patterns.get('has_tests', False) else 0
                practices['ci_cd'] += 1 if patterns.get('has_ci', False) else 0
                practices['documentation'] += 1 if patterns.get('has_docs', False) else 0
                practices['code_quality'] += 1 if patterns.get('has_linter', False) else 0
                practices['oop'] += 1 if patterns.get('uses_oop', False) else 0
                practices['functional'] += 1 if patterns.get('uses_functional', False) else 0
        
        # Calculate percentages for languages
        total_bytes = sum(all_languages.values())
        language_percentages = {}
        
        if total_bytes > 0:
            for lang, bytes_count in all_languages.most_common():
                percentage = (bytes_count / total_bytes) * 100
                language_percentages[lang] = {
                    'bytes': bytes_count,
                    'percentage': round(percentage, 2)
                }
        
        # Calculate average code metrics
        avg_metrics = {
            'complexity': round(sum(code_metrics['avg_complexity']) / len(code_metrics['avg_complexity']), 2) 
                if code_metrics['avg_complexity'] else 0,
            'function_size': round(sum(code_metrics['avg_function_size']) / len(code_metrics['avg_function_size']), 2)
                if code_metrics['avg_function_size'] else 0,
            'total_functions': code_metrics['total_functions']
        }
        
        # Calculate practice usage percentages
        repo_count = len(github_data['repos'])
        practice_percentages = {}
        if repo_count > 0:
            for practice, count in practices.items():
                practice_percentages[practice] = round((count / repo_count) * 100, 2)
        
        # Prepare the final summary
        skills_summary = {
            'user': self.username,
            'languages': language_percentages,
            'top_libraries': dict(all_libraries.most_common(10)),
            'frameworks': list(set(all_frameworks)),  # Remove duplicates
            'code_metrics': avg_metrics,
            'practices': practice_percentages,
            'repo_count': repo_count
        }
        
        # Cache the results
        cache.set(cache_key, skills_summary, settings.GITHUB_CACHE_TIMEOUT)
        return skills_summary