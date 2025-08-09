# Multi-Agent Code Review System - Complete Setup Guide

This comprehensive guide will walk you through setting up the automated multi-agent code review system from scratch. Perfect for team members who need to get the system running on their machine.

## 🎯 What This System Does

This system automatically reviews pull requests on GitHub using three specialized AI agents:
- **Code Quality Agent**: Checks for best practices and code standards
- **Security Agent**: Identifies vulnerabilities and security issues
- **Performance Agent**: Finds performance bottlenecks and inefficiencies

## 🚀 Quick Start for Team Members

If your team already has a Modal workspace set up, skip to [Simplified Team Member Setup](#simplified-team-member-setup).

## ⚠️ Critical Setup Points
1. Modal secrets MUST be named exactly `openaisecret` and `githubsecret`
2. GitHub webhook Content-type MUST be `application/json`
3. The webhook URL must end with `/webhook`
4. Use Python 3.11+ for compatibility

## 📋 Prerequisites

Before starting, you'll need:
- [ ] Python 3.11 or higher installed ([Download Python](https://www.python.org/downloads/))
- [ ] Git installed ([Download Git](https://git-scm.com/downloads))
- [ ] GitHub account
- [ ] OpenAI API key ([Get API Key](https://platform.openai.com/api-keys))
- [ ] Code editor (VS Code recommended)

## Step 1: Clone the Repository and Set Up Python Environment

### 1.1 Clone the Repository
```bash
# Clone the repository
git clone https://github.com/Rockazim/CECS-327.git
cd CECS-327
```

### 1.2 Create Virtual Environment
A virtual environment keeps dependencies isolated from your system Python.

```bash
# Create virtual environment
python -m venv venv

# If the above doesn't work, try:
python3 -m venv venv
```

### 1.3 Activate Virtual Environment

**Windows (Command Prompt):**
```bash
venv\Scripts\activate
```

**Windows (PowerShell):**
```bash
.\venv\Scripts\Activate.ps1
# If you get an error about execution policies, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Mac/Linux:**
```bash
source venv/bin/activate
```

You should see `(venv)` at the beginning of your command prompt.

### 1.4 Install Dependencies
```bash
# Upgrade pip first
python -m pip install --upgrade pip

# Install all required packages
pip install -r requirements.txt

# Install Modal separately (sometimes helps with compatibility)
pip install modal
```

### 1.5 Verify Installation
```bash
# Check Python version (should be 3.11+)
python --version

# Check Modal is installed
modal --version

# Check key packages
pip list | grep -E "openai|modal|autogen"
```

## Step 2: Set Up Modal Account and Authentication

### 2.1 Create Modal Account
1. Go to [https://modal.com](https://modal.com)
2. Click "Sign up" and create a free account
3. Verify your email

### 2.2 Authenticate Modal CLI
```bash
# Run Modal setup (make sure venv is activated)
modal setup

# This will:
# 1. Open your browser
# 2. Ask you to log in to Modal
# 3. Generate an authentication token
# 4. Save it locally
```

If the browser doesn't open automatically, you'll see a link - copy and paste it into your browser.

### 2.3 Verify Modal Connection
```bash
# Test that Modal is working
modal hello

# You should see "Hello, World!" output
```

## Step 3: Configure Modal Secrets

Modal secrets store your API keys securely in the cloud.

### 3.1 Get Your OpenAI API Key
1. Go to [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Click "Create new secret key"
3. Name it "Modal Code Review"
4. Copy the key (starts with `sk-`)
5. **Save it somewhere safe** - you can't see it again!

### 3.2 Create Modal Secrets via Web Interface
1. Go to [https://modal.com/secrets](https://modal.com/secrets)
2. Click "Create secret"

**Create OpenAI Secret:**
- Name: `openaisecret` (⚠️ MUST be exactly this name)
- Type: Custom
- Add key-value pair:
  - Key: `OPENAI_API_KEY`
  - Value: `[Your OpenAI API key from step 3.1]`
- Click "Create"

**Create GitHub Secret:**
- Name: `githubsecret` (⚠️ MUST be exactly this name)
- Type: Custom
- Add key-value pair:
  - Key: `GITHUB_TOKEN`
  - Value: `[We'll create this in Step 4]`
- Click "Create" (you'll update this after getting the token)

## Step 4: Create GitHub Personal Access Token

### 4.1 Generate the Token
1. Go to [https://github.com/settings/tokens/new](https://github.com/settings/tokens/new)
2. You might need to confirm your password
3. Configure the token:
   - **Note**: "Modal Code Review Bot"
   - **Expiration**: 90 days (recommended)
   - **Select scopes** - Check these boxes:
     - ✅ `repo` (Full control of private repositories)
     - ✅ `write:discussion` (Write access to discussions)

4. Scroll down and click "Generate token"
5. **IMPORTANT**: Copy the token immediately (starts with `ghp_`)
6. Save it somewhere secure - you can't see it again!

### 4.2 Update Modal Secret with GitHub Token
1. Go back to [https://modal.com/secrets](https://modal.com/secrets)
2. Click on `githubsecret`
3. Update the value of `GITHUB_TOKEN` with your newly created token
4. Click "Save"

## Step 5: Deploy to Modal

### 5.1 Deploy the Application
Make sure you're in the project root directory with virtual environment activated.

```bash
# Deploy to Modal
modal deploy modal_app/webhook_handler.py
```

### 5.2 Understanding the Output
You should see output like:
```
✓ Created objects.
├── 🔨 Created mount /path/to/webhook_handler.py
├── 🔨 Created mount /path/to/project
├── 🔨 Created web function create_app => https://[username]--multi-agent-code-review-create-app.modal.run
└── 🔨 Created function process_pr_review.
```

### 5.3 Save Your Webhook URL
**CRITICAL**: Copy the URL from the output and add `/webhook` to the end:
- From output: `https://[username]--multi-agent-code-review-create-app.modal.run`
- Your webhook URL: `https://[username]--multi-agent-code-review-create-app.modal.run/webhook`

Save this URL - you'll need it for GitHub webhook configuration!

## Step 6: Configure GitHub Webhook

### 6.1 Navigate to Webhook Settings
1. Go to your repository on GitHub
2. Click "Settings" tab
3. In the left sidebar, click "Webhooks"
4. Direct URL: `https://github.com/[username]/[repo]/settings/hooks`

### 6.2 Create New Webhook
1. Click "Add webhook" button
2. Configure the webhook:

**Payload URL**: 
- Paste your Modal webhook URL from Step 5.3
- ⚠️ **MUST end with `/webhook`**
- Example: `https://yourname--multi-agent-code-review-create-app.modal.run/webhook`

**Content type**:
- Select `application/json` 
- ⚠️ **CRITICAL**: Do NOT use `application/x-www-form-urlencoded`

**Secret**:
- Leave empty for now (optional security feature)

**SSL verification**:
- Leave as "Enable SSL verification"

**Which events would you like to trigger this webhook?**
- Select "Let me select individual events"
- Scroll down and check ONLY:
  - ✅ Pull requests
- Uncheck all other events

**Active**:
- ✅ Make sure this is checked

3. Click "Add webhook" (green button at bottom)

### 6.3 Verify Webhook is Working
After adding the webhook, you should see:
- A green checkmark ✓ next to your webhook
- "Last delivery was successful" message

If you see a red X, click on it to see the error details.

## Step 7: Test the System with a Pull Request

### 7.1 Create a Test Branch
```bash
# Make sure you're in the project directory
cd CECS-327

# Create and switch to a new branch
git checkout -b test-bot-review
```

### 7.2 Create a Test File with Issues
Create a new file called `test_review.py`:

```python
# test_review.py
# This file contains intentional issues for testing

import os
import subprocess

# Security Issue: Hardcoded password
DATABASE_PASSWORD = "admin123"
API_KEY = "sk-1234567890abcdef"

def get_user_data(user_id):
    # Security Issue: SQL Injection vulnerability
    query = f"SELECT * FROM users WHERE id = {user_id}"
    print(f"Executing: {query}")
    return query

def process_files(directory):
    # Performance Issue: Inefficient nested loops
    files = os.listdir(directory)
    for file1 in files:
        for file2 in files:
            for file3 in files:
                if file1 == file2 == file3:
                    print(f"Found match: {file1}")

def execute_command(user_input):
    # Security Issue: Command injection
    os.system(f"echo Processing: {user_input}")
    
# Code Quality Issue: No error handling
def risky_operation():
    data = open("important.txt").read()
    return eval(data)  # Security issue: eval() usage
```

### 7.3 Commit and Push
```bash
# Add the test file
git add test_review.py

# Commit with a message
git commit -m "Add test file for bot review"

# Push to GitHub
git push -u origin test-bot-review
```

### 7.4 Create Pull Request
1. Go to your repository on GitHub
2. You should see a yellow banner saying "test-bot-review had recent pushes"
3. Click "Compare & pull request"
4. Fill in:
   - **Title**: "Test PR for Code Review Bot"
   - **Description**: "Testing the multi-agent code review system"
5. Click "Create pull request"

### 7.5 Wait for Bot Review
- The bot should respond within 1-2 minutes
- You'll see "Checks" running on the PR
- A detailed comment will appear with findings from all three agents

### 7.6 Expected Results
The bot should identify:
- 🔴 **Security Issues**: Hardcoded passwords, SQL injection, command injection
- 🟡 **Performance Issues**: O(n³) complexity from triple nested loops
- 🟠 **Code Quality Issues**: No error handling, use of eval()

## Step 8: Troubleshooting Guide

### 8.1 Monitoring Tools

**View Modal Logs:**
```bash
# See real-time logs
modal logs multi-agent-code-review --follow

# See last 50 log entries
modal logs multi-agent-code-review -n 50
```

**Check Webhook Deliveries:**
1. Go to Settings → Webhooks → Your webhook
2. Click "Recent Deliveries" tab
3. Look for:
   - ✅ Green checkmark = successful delivery
   - ❌ Red X = failed delivery (click to see error)

### 8.2 Common Issues and Solutions

#### Issue: "404 Not Found" on Webhook
**Symptoms**: GitHub shows 404 error in webhook deliveries
**Solutions**:
- Verify webhook URL ends with `/webhook`
- Check Modal deployment is active: `modal app list`
- Redeploy if needed: `modal deploy modal_app/webhook_handler.py`

#### Issue: "Invalid JSON" Error
**Symptoms**: Webhook fails with JSON parsing error
**Solutions**:
- In GitHub webhook settings, ensure Content-type is `application/json`
- NOT `application/x-www-form-urlencoded`

#### Issue: "Missing API Key" or Authentication Errors
**Symptoms**: Modal logs show authentication errors
**Solutions**:
1. Check secret names in Modal:
   ```bash
   # List your secrets
   modal secret list
   ```
2. Verify names are EXACTLY:
   - `openaisecret` (not `openai-secret` or `OPENAI_SECRET`)
   - `githubsecret` (not `github-secret` or `GITHUB_SECRET`)
3. Check secret contents have the right keys:
   - `openaisecret` should have key `OPENAI_API_KEY`
   - `githubsecret` should have key `GITHUB_TOKEN`

#### Issue: Bot Doesn't Post Review
**Symptoms**: PR created but no bot comment appears
**Debugging Steps**:
1. Check Modal logs for errors:
   ```bash
   modal logs multi-agent-code-review --follow
   ```
2. Verify PR has code files (not just markdown/docs)
3. Check webhook was triggered in GitHub
4. Look for rate limiting messages

#### Issue: "Rate Limit Exceeded"
**Symptoms**: Bot stops working after several PRs
**Solutions**:
- OpenAI has rate limits - wait a few minutes
- Check your OpenAI usage dashboard
- Consider implementing caching (already included in code)

## Step 9: Working as a Team

### 9.1 Updating the System
When you or your teammates make changes to the code:

```bash
# Pull latest changes
git pull origin main

# Redeploy to Modal
modal deploy modal_app/webhook_handler.py
```

### 9.2 Team Setup Options

#### Option A: Shared Modal Workspace (Recommended)
**Benefits**: Easier setup, shared secrets, single deployment, unified logs

**For Team Lead (First Person):**
1. Go to [Modal Dashboard](https://modal.com/apps)
2. Click on your username (top right) → "Create workspace"
3. Name it (e.g., "CECS-327-Team")
4. Go to Workspace Settings → Members
5. Click "Invite members"
6. Add team members by email

**For Team Members:**
1. Accept the Modal workspace invitation via email
2. Run `modal config set-active-workspace [workspace-name]`
3. They can now use the deployed app without setting up secrets!

#### Option B: Individual Deployments
- Each team member needs their own Modal account
- Each person sets up their own secrets
- Each person deploys independently
- More complex but gives everyone full control

### 9.3 Making Your First Team PR
1. Create a feature branch:
   ```bash
   git checkout -b add-new-feature
   ```

2. Make your changes to the code

3. Commit and push:
   ```bash
   git add .
   git commit -m "Add new feature"
   git push -u origin add-new-feature
   ```

4. Create PR on GitHub - the bot will automatically review it!

## Quick Reference

### Key Commands
```bash
# Activate virtual environment
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# Deploy to Modal
modal deploy modal_app/webhook_handler.py

# View logs
modal logs multi-agent-code-review --follow

# Run tests
pytest tests/
```

### Important URLs
- Modal Dashboard: https://modal.com/apps
- Modal Secrets: https://modal.com/secrets
- GitHub Tokens: https://github.com/settings/tokens
- OpenAI API Keys: https://platform.openai.com/api-keys

### Architecture Overview
```
GitHub PR → Webhook → Modal → Orchestrator
                                    ↓
                        ┌─────────────────────────┐
                        │   Three AI Agents:      │
                        │   • Code Quality        │
                        │   • Security            │
                        │   • Performance         │
                        └─────────────────────────┘
                                    ↓
                            Consensus & Report
                                    ↓
                            GitHub PR Comment
```

## Need Help?

1. Check the Modal logs first
2. Verify webhook deliveries in GitHub
3. Ensure all secrets are correctly named
4. Check that you're using Python 3.11+
5. Make sure virtual environment is activated

## 🎉 Congratulations!

You now have a fully functional AI-powered code review system! Every pull request will be automatically reviewed by three specialized agents, providing comprehensive feedback on code quality, security, and performance.

### Next Steps
- Try creating PRs with different types of code
- Experiment with the review feedback
- Consider customizing the agents for your specific needs
- Monitor costs in your OpenAI dashboard

Happy coding! 🚀

---

## Simplified Team Member Setup

If your team lead has already set up a Modal workspace, follow these simplified steps:

### 1. Clone and Set Up Environment
```bash
# Clone the repository
git clone https://github.com/Rockazim/CECS-327.git
cd CECS-327

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Mac/Linux
# OR
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
pip install modal
```

### 2. Join Modal Workspace
1. Check your email for Modal workspace invitation
2. Accept the invitation
3. Set up Modal:
   ```bash
   modal setup
   ```
4. Switch to team workspace:
   ```bash
   modal config set-active-workspace [workspace-name]
   ```

### 3. Verify Access
```bash
# List apps in workspace (should see multi-agent-code-review)
modal app list

# Check logs to verify access
modal logs multi-agent-code-review -n 5
```

### 4. You're Done!
- No need to set up secrets (already configured in workspace)
- No need to deploy (already deployed by team lead)
- The webhook is already configured on GitHub
- Just create branches and PRs - the bot will review them automatically!

### Making Changes
If you need to update the code:
```bash
git pull origin main
# Make your changes
modal deploy modal_app/webhook_handler.py  # Only if you have deploy permissions
```