"""
Modal deployment of the agent orchestrator
This file packages all agents and utilities for Modal deployment
"""

import modal
import os
from typing import Dict, List, Any
import time
import logging

# Create Modal app
app = modal.App("multi-agent-orchestrator")

# Define the image with dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "autogen-agentchat==0.7.1",
        "autogen-ext[openai]==0.7.1", 
        "openai>=1.93",
        "python-dotenv"
    )
)

# Mount local code
code_mount = modal.Mount.from_local_dir(
    "../",  # Mount parent directory to get all code
    remote_path="/app",
    condition=lambda pth: not any(
        part.startswith('.') or part == '__pycache__' or part == 'venv'
        for part in pth.parts
    )
)


@app.function(
    image=image,
    secret=modal.Secret.from_name("openai-secret"),
    mounts=[code_mount],
    timeout=600,
    memory=2048,
    cpu=1.0,
    volumes={"/cache": modal.Volume.from_name("code-review-cache", create_if_missing=True)}
)
async def review_code(
    code: str,
    filename: str = "unknown",
    pr_description: str = "",
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Review code using the multi-agent orchestrator
    
    This is a Modal function that can be called remotely
    """
    import sys
    sys.path.append("/app")
    
    from orchestrator import SimpleMultiAgentOrchestrator
    from utils.cache_manager import get_cache_manager
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    start_time = time.time()
    
    # Initialize cache
    cache_manager = get_cache_manager(use_modal=True)
    
    # Check cache first
    cache_key_context = {"filename": filename, "pr_description": pr_description}
    cached_result = await cache_manager.get_async(code, "full_review", cache_key_context)
    
    if cached_result:
        logger.info(f"Cache hit for file: {filename}")
        cached_result["from_cache"] = True
        cached_result["processing_time"] = time.time() - start_time
        return cached_result
    
    logger.info(f"Cache miss for file: {filename}, performing review")
    
    # Initialize orchestrator
    openai_key = os.environ.get("OPENAI_API_KEY")
    orchestrator = SimpleMultiAgentOrchestrator(api_key=openai_key)
    
    # Perform review
    result = await orchestrator.review_code(
        code=code,
        filename=filename,
        pr_description=pr_description,
        context=context
    )
    
    # Cache the result
    if result.get("status") == "success":
        await cache_manager.set_async(code, "full_review", result, cache_key_context)
        logger.info(f"Cached review result for: {filename}")
    
    # Add performance metrics
    result["processing_time"] = time.time() - start_time
    result["cache_stats"] = cache_manager.get_stats()
    
    return result


@app.function(
    image=image,
    secret=modal.Secret.from_name("openai-secret"),
    mounts=[code_mount],
    timeout=900,
    memory=4096,
    cpu=2.0,
    retries=1
)
async def review_pull_request(
    pr_files: List[Dict[str, str]],
    pr_description: str = ""
) -> Dict[str, Any]:
    """Review an entire pull request
    
    This function handles multiple files with higher resource allocation
    """
    import sys
    sys.path.append("/app")
    
    from orchestrator import SimpleMultiAgentOrchestrator
    
    # Initialize orchestrator
    openai_key = os.environ.get("OPENAI_API_KEY")
    orchestrator = SimpleMultiAgentOrchestrator(api_key=openai_key)
    
    # Perform PR review
    result = await orchestrator.review_pull_request(
        pr_files=pr_files,
        pr_description=pr_description
    )
    
    return result


@app.function(
    image=image,
    secret=modal.Secret.from_name("openai-secret"),
    mounts=[code_mount],
    gpu="T4",  # Add GPU for performance-intensive analysis
    timeout=300,
    memory=8192
)
async def analyze_performance(code: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Specialized performance analysis with GPU support
    
    This demonstrates GPU allocation for compute-intensive tasks
    """
    import sys
    sys.path.append("/app")
    
    from agents.performance_analyzer import PerformanceAnalyzerAgent
    
    # Initialize agent
    openai_key = os.environ.get("OPENAI_API_KEY")
    agent = PerformanceAnalyzerAgent(api_key=openai_key)
    
    # Perform analysis
    result = await agent.analyze_code(code=code, context=context)
    
    # Additional GPU-accelerated analysis could go here
    # For example: AST parsing, complexity calculations, etc.
    
    return result


@app.local_entrypoint()
def test_orchestrator():
    """Test the Modal-deployed orchestrator"""
    import asyncio
    
    test_code = '''
def process_data(user_id):
    # SQL injection vulnerability
    query = f"SELECT * FROM users WHERE id = {user_id}"
    
    # Hardcoded password
    password = "admin123"
    
    # Inefficient algorithm
    data = fetch_data(query)
    for i in range(len(data)):
        for j in range(len(data)):
            if data[i] == data[j] and i != j:
                print("Duplicate found")
    
    return data
'''
    
    print("Testing Modal-deployed orchestrator...")
    print("="*60)
    
    # Test single file review
    with app.run():
        result = asyncio.run(review_code.remote(
            code=test_code,
            filename="test.py",
            pr_description="Test review on Modal"
        ))
        
        print(f"Review Status: {result.get('status')}")
        if result.get('status') == 'success':
            print(f"Consensus recommendations: {len(result.get('consensus_results', {}).get('recommendations', []))}")
            print("\nTest passed! ✅")
        else:
            print(f"Error: {result.get('error')}")
            print("\nTest failed! ❌")


if __name__ == "__main__":
    # This will be run when executing the file locally
    test_orchestrator()