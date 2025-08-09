"""
GitHub Integration for fetching PR files and posting reviews
"""

import os
import json
import httpx
from typing import Dict, List, Any, Optional
from datetime import datetime
import base64


class GitHubIntegration:
    """Handles GitHub API interactions for PR reviews"""
    
    def __init__(self, github_token: str = None):
        """Initialize GitHub integration
        
        Args:
            github_token: GitHub personal access token or app token
        """
        self.token = github_token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise ValueError("GitHub token is required")
        
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
    
    async def get_pr_files(self, owner: str, repo: str, pr_number: int) -> List[Dict[str, Any]]:
        """Fetch all files changed in a pull request
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            
        Returns:
            List of file information including content
        """
        async with httpx.AsyncClient() as client:
            # Get PR details
            pr_url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
            pr_response = await client.get(pr_url, headers=self.headers)
            pr_response.raise_for_status()
            pr_data = pr_response.json()
            
            # Get files changed in PR
            files_url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/files"
            files_response = await client.get(files_url, headers=self.headers)
            files_response.raise_for_status()
            files_data = files_response.json()
            
            # Process each file
            pr_files = []
            for file in files_data:
                if file['status'] in ['added', 'modified']:
                    file_info = {
                        'filename': file['filename'],
                        'status': file['status'],
                        'additions': file['additions'],
                        'deletions': file['deletions'],
                        'changes': file['changes'],
                        'patch': file.get('patch', ''),
                        'content': await self._get_file_content(
                            owner, repo, file['filename'], pr_data['head']['sha'], client
                        )
                    }
                    
                    # Determine language from extension
                    extension = os.path.splitext(file['filename'])[1]
                    language_map = {
                        '.py': 'python',
                        '.js': 'javascript',
                        '.ts': 'typescript',
                        '.java': 'java',
                        '.cpp': 'cpp',
                        '.c': 'c',
                        '.go': 'go',
                        '.rs': 'rust'
                    }
                    file_info['language'] = language_map.get(extension, 'text')
                    
                    pr_files.append(file_info)
            
            return pr_files
    
    async def _get_file_content(self, owner: str, repo: str, path: str, ref: str, client: httpx.AsyncClient) -> str:
        """Get the content of a specific file
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: File path
            ref: Git reference (commit SHA, branch, tag)
            client: HTTP client instance
            
        Returns:
            File content as string
        """
        content_url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}?ref={ref}"
        
        try:
            response = await client.get(content_url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            # GitHub returns content base64 encoded
            if 'content' in data:
                content_bytes = base64.b64decode(data['content'])
                return content_bytes.decode('utf-8')
            else:
                return "# File content not available"
                
        except Exception as e:
            print(f"Error fetching file content for {path}: {str(e)}")
            return f"# Error fetching file content: {str(e)}"
    
    async def post_review_comment(self, 
                                 owner: str, 
                                 repo: str, 
                                 pr_number: int, 
                                 review_body: str,
                                 event: str = "COMMENT") -> Dict[str, Any]:
        """Post a review comment on a pull request
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            review_body: The review content in markdown
            event: Review event type (COMMENT, APPROVE, REQUEST_CHANGES)
            
        Returns:
            API response
        """
        async with httpx.AsyncClient() as client:
            try:
                # First check if PR exists and is open
                pr_url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
                pr_response = await client.get(pr_url, headers=self.headers)
                
                if pr_response.status_code == 404:
                    print(f"PR #{pr_number} not found")
                    return {"error": "PR not found", "status": 404}
                
                pr_data = pr_response.json()
                if pr_data.get('state') != 'open':
                    print(f"PR #{pr_number} is {pr_data.get('state')}, not open")
                    # For closed PRs, just post a comment instead of a review
                    comment_url = f"{self.base_url}/repos/{owner}/{repo}/issues/{pr_number}/comments"
                    comment_response = await client.post(
                        comment_url,
                        headers=self.headers,
                        json={"body": review_body}
                    )
                    return comment_response.json()
                
                # Check if the bot is the PR author (can't review own PRs)
                current_user_url = f"{self.base_url}/user"
                user_response = await client.get(current_user_url, headers=self.headers)
                if user_response.status_code == 200:
                    current_user = user_response.json()
                    if current_user.get('login') == pr_data.get('user', {}).get('login'):
                        print(f"Cannot review own PR")
                        # Post as comment instead
                        comment_url = f"{self.base_url}/repos/{owner}/{repo}/issues/{pr_number}/comments"
                        comment_response = await client.post(
                            comment_url,
                            headers=self.headers,
                            json={"body": review_body}
                        )
                        return comment_response.json()
                
                # Truncate body if too long
                max_body_length = 65536
                if len(review_body) > max_body_length:
                    review_body = review_body[:max_body_length - 100] + "\n\n... (truncated due to length)"
                
                # Try to post the review
                review_url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
                payload = {
                    "body": review_body,
                    "event": event
                }
                
                response = await client.post(
                    review_url,
                    headers=self.headers,
                    json=payload
                )
                
                # Log response for debugging
                if response.status_code not in [200, 201]:
                    print(f"GitHub API Response Status: {response.status_code}")
                    print(f"Response Body: {response.text}")
                    
                    # If review fails, try posting as a regular comment
                    if response.status_code == 422:
                        print("Review failed with 422, posting as comment instead")
                        comment_url = f"{self.base_url}/repos/{owner}/{repo}/issues/{pr_number}/comments"
                        comment_response = await client.post(
                            comment_url,
                            headers=self.headers,
                            json={"body": review_body}
                        )
                        return comment_response.json()
                
                response.raise_for_status()
                return response.json()
                
            except Exception as e:
                print(f"Error posting review: {str(e)}")
                # Try to post as a simple comment as fallback
                try:
                    comment_url = f"{self.base_url}/repos/{owner}/{repo}/issues/{pr_number}/comments"
                    comment_response = await client.post(
                        comment_url,
                        headers=self.headers,
                        json={"body": f"**Code Review Results**\n\n{review_body}"}
                    )
                    return comment_response.json()
                except:
                    raise e
    
    async def post_inline_comments(self,
                                  owner: str,
                                  repo: str,
                                  pr_number: int,
                                  comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Post inline comments on specific lines
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            comments: List of comment objects with path, line, and body
            
        Returns:
            List of created comments
        """
        async with httpx.AsyncClient() as client:
            # First need to get the latest commit SHA
            pr_url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
            pr_response = await client.get(pr_url, headers=self.headers)
            pr_response.raise_for_status()
            pr_data = pr_response.json()
            commit_sha = pr_data['head']['sha']
            
            created_comments = []
            
            for comment in comments:
                comment_url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/comments"
                
                payload = {
                    "body": comment['body'],
                    "commit_id": commit_sha,
                    "path": comment['path'],
                    "line": comment.get('line', 1),
                    "side": "RIGHT"  # Comment on the new version
                }
                
                try:
                    response = await client.post(
                        comment_url,
                        headers=self.headers,
                        json=payload
                    )
                    response.raise_for_status()
                    created_comments.append(response.json())
                except Exception as e:
                    print(f"Error posting inline comment: {str(e)}")
            
            return created_comments
    
    async def get_pr_info(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        """Get detailed PR information
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            
        Returns:
            PR metadata
        """
        async with httpx.AsyncClient() as client:
            pr_url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
            response = await client.get(pr_url, headers=self.headers)
            response.raise_for_status()
            
            pr_data = response.json()
            
            return {
                'title': pr_data['title'],
                'description': pr_data.get('body', ''),
                'author': pr_data['user']['login'],
                'state': pr_data['state'],
                'created_at': pr_data['created_at'],
                'updated_at': pr_data['updated_at'],
                'base_branch': pr_data['base']['ref'],
                'head_branch': pr_data['head']['ref'],
                'mergeable': pr_data.get('mergeable'),
                'additions': pr_data['additions'],
                'deletions': pr_data['deletions'],
                'changed_files': pr_data['changed_files']
            }
    
    def format_review_comment(self, markdown_report: str, pr_info: Dict[str, Any]) -> str:
        """Format the review report for GitHub comment
        
        Args:
            markdown_report: The generated markdown report
            pr_info: PR metadata
            
        Returns:
            Formatted comment
        """
        # Add PR context header
        header = f"""## 🤖 Automated Code Review
        
This review was generated by the Multi-Agent Code Review System.

**PR:** {pr_info.get('title', 'Untitled')}
**Author:** @{pr_info.get('author', 'unknown')}
**Files Changed:** {pr_info.get('changed_files', 0)}

---

"""
        
        # Add the main report
        formatted_report = header + markdown_report
        
        # Add footer with metadata
        footer = f"""

---

*Review completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}*
*Powered by Multi-Agent Code Review System (v1.0)*
"""
        
        return formatted_report + footer
    
    async def check_rate_limit(self) -> Dict[str, Any]:
        """Check GitHub API rate limit status
        
        Returns:
            Rate limit information
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/rate_limit",
                headers=self.headers
            )
            response.raise_for_status()
            
            data = response.json()
            core_limits = data['rate']
            
            return {
                'limit': core_limits['limit'],
                'remaining': core_limits['remaining'],
                'reset': datetime.fromtimestamp(core_limits['reset']).isoformat(),
                'used': core_limits['used']
            }