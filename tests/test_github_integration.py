#!/usr/bin/env python3
"""
Test script for GitHub Integration
"""

import asyncio
import os
from dotenv import load_dotenv
from utils.github_integration import GitHubIntegration

# Load environment variables
load_dotenv()


async def test_rate_limit():
    """Test GitHub API connection and rate limit"""
    print("="*60)
    print("Testing GitHub API Connection")
    print("="*60)
    
    github = GitHubIntegration()
    
    try:
        rate_limit = await github.check_rate_limit()
        print("✓ Successfully connected to GitHub API")
        print(f"  Rate Limit: {rate_limit['remaining']}/{rate_limit['limit']}")
        print(f"  Reset Time: {rate_limit['reset']}")
        return True
    except Exception as e:
        print(f"✗ Failed to connect to GitHub API: {str(e)}")
        return False


async def test_pr_fetching():
    """Test fetching PR information"""
    print("\n" + "="*60)
    print("Testing PR File Fetching")
    print("="*60)
    
    # You'll need to update these with a real repo and PR number
    # For testing, you can use a public repo with an open PR
    owner = "microsoft"  # Example: microsoft
    repo = "vscode"      # Example: vscode
    pr_number = 1        # Example: 1
    
    print(f"Testing with {owner}/{repo} PR #{pr_number}")
    print("(This is just a connectivity test - update with your own repo for real testing)")
    
    github = GitHubIntegration()
    
    try:
        # Get PR info
        pr_info = await github.get_pr_info(owner, repo, pr_number)
        print(f"\n✓ PR Title: {pr_info['title']}")
        print(f"  Author: {pr_info['author']}")
        print(f"  Files Changed: {pr_info['changed_files']}")
        
        # Get PR files
        pr_files = await github.get_pr_files(owner, repo, pr_number)
        print(f"\n✓ Successfully fetched {len(pr_files)} files")
        
        if pr_files:
            print("\nFirst file:")
            print(f"  Name: {pr_files[0]['filename']}")
            print(f"  Status: {pr_files[0]['status']}")
            print(f"  Language: {pr_files[0]['language']}")
            print(f"  Changes: +{pr_files[0]['additions']} -{pr_files[0]['deletions']}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        print("\nThis is expected if:")
        print("1. The PR doesn't exist")
        print("2. You don't have access to the repository")
        print("3. Your token doesn't have the required permissions")
        return False


async def test_webhook_signature():
    """Test webhook signature verification"""
    print("\n" + "="*60)
    print("Testing Webhook Signature Verification")
    print("="*60)
    
    from webhook_handler import verify_webhook_signature
    
    # Test data
    payload = b'{"action": "opened", "number": 1}'
    secret = "test-secret"
    
    # Generate valid signature
    import hmac
    import hashlib
    valid_signature = 'sha256=' + hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    # Test valid signature
    result = verify_webhook_signature(payload, valid_signature, secret)
    print(f"✓ Valid signature test: {'PASSED' if result else 'FAILED'}")
    
    # Test invalid signature
    invalid_signature = 'sha256=' + 'invalid'
    result = verify_webhook_signature(payload, invalid_signature, secret)
    print(f"✓ Invalid signature test: {'PASSED' if not result else 'FAILED'}")
    
    return True


def test_webhook_server():
    """Instructions for testing the webhook server"""
    print("\n" + "="*60)
    print("Webhook Server Testing Instructions")
    print("="*60)
    
    print("\n1. Start the webhook server:")
    print("   python webhook_handler.py")
    
    print("\n2. Use ngrok to expose your local server:")
    print("   ngrok http 8000")
    
    print("\n3. Configure GitHub webhook:")
    print("   - Go to your repository settings")
    print("   - Click 'Webhooks' -> 'Add webhook'")
    print("   - Payload URL: https://YOUR-NGROK-URL.ngrok.io/webhook")
    print("   - Content type: application/json")
    print("   - Secret: (set if using GITHUB_WEBHOOK_SECRET)")
    print("   - Events: Pull requests")
    
    print("\n4. Create or update a PR to trigger the webhook")
    
    print("\n5. Check the server logs for processing output")


async def main():
    """Run all tests"""
    print("GitHub Integration Test Suite")
    print("="*60)
    
    # Check for GitHub token
    if not os.getenv("GITHUB_TOKEN"):
        print("Error: GITHUB_TOKEN not found in environment variables")
        print("\nTo set up GitHub token:")
        print("1. Go to https://github.com/settings/tokens")
        print("2. Generate new token (classic)")
        print("3. Select scopes: repo (all)")
        print("4. Add to .env file: GITHUB_TOKEN=your-token-here")
        return
    
    # Run tests
    tests_passed = 0
    
    if await test_rate_limit():
        tests_passed += 1
    
    if await test_pr_fetching():
        tests_passed += 1
    
    if await test_webhook_signature():
        tests_passed += 1
    
    # Show webhook testing instructions
    test_webhook_server()
    
    print("\n" + "="*60)
    print(f"Tests completed: {tests_passed}/3 passed")
    print("="*60)
    
    if tests_passed == 3:
        print("\n✅ All tests passed! GitHub integration is ready.")
        print("\nNext steps:")
        print("1. Update requirements.txt with: httpx fastapi uvicorn")
        print("2. Set up a GitHub webhook on your repository")
        print("3. Use ngrok to test locally or deploy to Modal")
    else:
        print("\n⚠️  Some tests failed. Please check your configuration.")


if __name__ == "__main__":
    asyncio.run(main())