"""
Modal deployment of the GitHub webhook handler
"""

import modal
import os
import json
import hmac
import hashlib
from datetime import datetime

# Create Modal app
app = modal.App("multi-agent-code-review")

# Define the image with all dependencies
from pathlib import Path

project_root = Path(__file__).parent.parent  # Go up to project root

def should_ignore(path):
    """Ignore unnecessary files and folders"""
    path_str = str(path)
    ignore_patterns = ['venv', '__pycache__', '.git', '.pytest_cache', '*.pyc', '.env']
    return any(pattern in path_str for pattern in ignore_patterns)

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "autogen-agentchat==0.7.1",
        "autogen-ext[openai]==0.7.1",
        "openai>=1.93",
        "httpx",
        "fastapi[standard]",
        "python-dotenv",
        "cryptography"
    )
    .add_local_dir(project_root, remote_path="/project", ignore=should_ignore)
)

# Create volume for caching (optional)
volume = modal.Volume.from_name("code-review-cache", create_if_missing=True)

# Import secrets
secrets = [
    modal.Secret.from_name("openaisecret"),
    modal.Secret.from_name("githubsecret")
]



@app.function(
    image=image,
    secrets=secrets,
    volumes={"/cache": volume},
    timeout=600,  # 10 minutes max per review
    memory=2048,  # 2GB RAM
)
@modal.asgi_app()
def create_app():
    from fastapi import FastAPI, Request, Header, HTTPException
    from fastapi.responses import JSONResponse
    
    app = FastAPI()
    
    @app.post("/webhook")
    async def webhook(request: Request, x_hub_signature_256: str = Header(None), x_github_event: str = Header(None)):
        """Handle GitHub webhook events on Modal
        
        Args:
            request: Dict containing headers and body from the webhook
            
        Returns:
            Response dict
        """
        import sys
        sys.path.append("/project")
        
        from orchestrator import SimpleMultiAgentOrchestrator
        from utils.github_integration import GitHubIntegration
        
        # Get request body
        body = await request.body()
        
        # Parse event type
        event_type = x_github_event or ""
        signature = x_hub_signature_256 or ""
        
        # Verify signature if secret is configured
        webhook_secret = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
        if webhook_secret and not verify_signature(body, signature, webhook_secret):
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse JSON payload
        try:
            # GitHub webhooks send JSON even with form-encoded content type
            if body:
                payload = json.loads(body.decode('utf-8') if isinstance(body, bytes) else body)
            else:
                # Try to get JSON directly from request
                payload = await request.json()
        except (json.JSONDecodeError, ValueError) as e:
            # Log the error for debugging
            print(f"Failed to parse JSON: {e}")
            print(f"Body type: {type(body)}")
            print(f"Body content: {body[:200] if body else 'Empty'}")
            raise HTTPException(status_code=400, detail="Invalid JSON")
        
        # Handle ping event
        if event_type == "ping":
            return JSONResponse(content={"message": "Pong! Webhook configured successfully."})
        
        # Handle pull request events
        if event_type == "pull_request":
            action = payload.get("action", "")
            if action not in ["opened", "synchronize", "reopened"]:
                return JSONResponse(content={"message": f"Ignoring action: {action}"})
            
            # Process in background using Modal's spawn
            process_pr_review.spawn(payload)
            
            return JSONResponse(content={
                "message": f"Review initiated for PR #{payload['pull_request']['number']}"
            })
        
        return JSONResponse(content={"message": f"Event '{event_type}' not supported"})
    
    @app.get("/")
    async def health_check():
        return {
            "status": "healthy",
            "service": "Multi-Agent Code Review (Modal)",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        }
    
    return app


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook signature"""
    if not signature or not signature.startswith('sha256='):
        return False
    
    expected = 'sha256=' + hmac.new(
        secret.encode('utf-8'),
        payload if isinstance(payload, bytes) else payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature)


@app.function(
    image=image,
    secrets=secrets,
    volumes={"/cache": volume},
    timeout=1200,  # 20 minutes for full PR review
    memory=4096,   # 4GB RAM
    cpu=2.0,       # 2 CPU cores
)
async def process_pr_review(webhook_payload: dict):
    """Process a pull request review
    
    This runs as a separate Modal function to handle long-running reviews
    """
    import sys
    sys.path.append("/project")
    
    from orchestrator import SimpleMultiAgentOrchestrator
    from utils.github_integration import GitHubIntegration
    
    try:
        # Extract PR information
        pr_data = webhook_payload["pull_request"]
        repo_data = webhook_payload["repository"]
        
        owner = repo_data["owner"]["login"]
        repo = repo_data["name"]
        pr_number = pr_data["number"]
        pr_title = pr_data["title"]
        pr_description = pr_data.get("body", "")
        
        print(f"Processing PR #{pr_number}: {pr_title}")
        print(f"Repository: {owner}/{repo}")
        
        # Initialize GitHub integration
        # Try different possible environment variable names Modal might use
        github_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("githubsecret") or os.environ.get("GITHUBSECRET")
        if not github_token:
            print("ERROR: GitHub token not found. Available env vars:")
            print([k for k in os.environ.keys() if 'github' in k.lower() or 'token' in k.lower()])
            raise ValueError("GitHub token is required")
        github = GitHubIntegration(github_token=github_token)
        
        # Get PR files
        pr_files = await github.get_pr_files(owner, repo, pr_number)
        
        if not pr_files:
            await github.post_review_comment(
                owner, repo, pr_number,
                "No files found to review in this pull request.",
                "COMMENT"
            )
            return
        
        # Filter for code files
        code_extensions = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs', '.rb', '.php'}
        reviewable_files = []
        
        for file in pr_files:
            extension = os.path.splitext(file['filename'])[1]
            if extension in code_extensions:
                reviewable_files.append({
                    'filename': file['filename'],
                    'content': file['content'],
                    'language': file['language']
                })
        
        if not reviewable_files:
            await github.post_review_comment(
                owner, repo, pr_number,
                "No code files found to review. Supported extensions: " + ", ".join(code_extensions),
                "COMMENT"
            )
            return
        
        print(f"Reviewing {len(reviewable_files)} code files...")
        
        # Initialize orchestrator
        openai_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("openaisecret") or os.environ.get("OPENAISECRET")
        orchestrator = SimpleMultiAgentOrchestrator(api_key=openai_key)
        
        # Get PR metadata
        pr_info = await github.get_pr_info(owner, repo, pr_number)
        
        # Perform review
        review_result = await orchestrator.review_pull_request(
            pr_files=reviewable_files,
            pr_description=pr_description
        )
        
        # Format and post review
        if review_result.get('markdown_report'):
            formatted_comment = github.format_review_comment(
                review_result['markdown_report'],
                pr_info
            )
            
            # Determine review event
            summary = review_result.get('overall_summary', {})
            total_issues = summary.get('total_issues', {})
            
            if total_issues.get('security', 0) > 0:
                event = "REQUEST_CHANGES"
            elif sum(total_issues.values()) > 0:
                event = "COMMENT"
            else:
                event = "APPROVE"
            
            # Post the review
            review_response = await github.post_review_comment(
                owner, repo, pr_number,
                formatted_comment,
                event
            )
            
            print(f"Review posted successfully: {review_response.get('html_url', 'No URL')}")
            
            # Save to cache volume for debugging
            cache_path = f"/cache/reviews/pr_{pr_number}_{datetime.now().isoformat()}.md"
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, 'w') as f:
                f.write(formatted_comment)
    
    except Exception as e:
        print(f"Error processing PR: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Try to post error comment
        try:
            github = GitHubIntegration(github_token=os.environ.get("GITHUB_TOKEN") or os.environ.get("githubsecret") or os.environ.get("GITHUBSECRET"))
            await github.post_review_comment(
                owner, repo, pr_number,
                f"An error occurred while reviewing this pull request. Please check the logs.",
                "COMMENT"
            )
        except:
            pass


# Health check is now part of the FastAPI app above


@app.local_entrypoint()
def deploy_info():
    """Show deployment information"""
    print("Modal Deployment Information:")
    print("="*60)
    print("App Name: multi-agent-code-review")
    print("\nEndpoints:")
    print("- Webhook: https://[your-modal-username]--multi-agent-code-review-webhook.modal.run")
    print("- Health: https://[your-modal-username]--multi-agent-code-review-health-check.modal.run")
    print("\nTo deploy: modal deploy modal_app/webhook_handler.py")
    print("\nRequired secrets in Modal:")
    print("- openai-secret: OPENAI_API_KEY")
    print("- github-secret: GITHUB_TOKEN, GITHUB_WEBHOOK_SECRET (optional)")
    print("="*60)