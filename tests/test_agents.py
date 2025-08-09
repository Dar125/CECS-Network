#!/usr/bin/env python3
"""
Test script for the three specialized agents
"""

import asyncio
import os
from dotenv import load_dotenv
from agents.code_reviewer import CodeReviewerAgent
from agents.security_checker import SecurityCheckerAgent
from agents.performance_analyzer import PerformanceAnalyzerAgent

# Load environment variables
load_dotenv()

# Sample code for testing
SAMPLE_CODE = """
def process_user_data(user_id, connection_string):
    # Connect to database
    import sqlite3
    conn = sqlite3.connect(connection_string)
    cursor = conn.cursor()
    
    # Get user data - potential SQL injection
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    user_data = cursor.fetchone()
    
    # Process all orders for user - potential N+1 problem
    orders = []
    for i in range(100):
        order_query = f"SELECT * FROM orders WHERE user_id = {user_id} AND order_id = {i}"
        cursor.execute(order_query)
        order = cursor.fetchone()
        if order:
            orders.append(order)
    
    # Bubble sort orders by date - inefficient algorithm
    for i in range(len(orders)):
        for j in range(0, len(orders)-i-1):
            if orders[j][2] > orders[j+1][2]:  # Assuming date is at index 2
                orders[j], orders[j+1] = orders[j+1], orders[j]
    
    # Store password in plain text - security issue
    password = "admin123"
    
    # No error handling
    result = {"user": user_data, "orders": orders, "password": password}
    
    conn.close()
    return result
"""


async def test_code_reviewer():
    """Test the Code Reviewer Agent"""
    print("=" * 60)
    print("Testing Code Reviewer Agent")
    print("=" * 60)
    
    print("Creating CodeReviewerAgent...")
    agent = CodeReviewerAgent()
    print("✓ Agent created successfully")
    
    print("Calling analyze_code (this may take 10-30 seconds)...")
    result = await agent.analyze_code(
        code=SAMPLE_CODE,
        filename="test_sample.py",
        context={"language": "python", "pr_description": "Added user data processing function"}
    )
    print("✓ Analysis complete")
    
    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        print(f"Issues found: {result['issues_found']}")
        print("\nReview:")
        print("-" * 40)
        print(result['review'])
    else:
        print(f"Error: {result['error']}")
    
    return result


async def test_security_checker():
    """Test the Security Checker Agent"""
    print("\n" + "=" * 60)
    print("Testing Security Checker Agent")
    print("=" * 60)
    
    print("Creating SecurityCheckerAgent...")
    agent = SecurityCheckerAgent()
    print("✓ Agent created successfully")
    
    print("Calling analyze_code (this may take 10-30 seconds)...")
    result = await agent.analyze_code(
        code=SAMPLE_CODE,
        filename="test_sample.py",
        context={"language": "python", "framework": "sqlite3"}
    )
    print("✓ Analysis complete")
    
    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        print(f"Vulnerabilities found: {result['vulnerabilities']}")
        print("\nSecurity Analysis:")
        print("-" * 40)
        print(result['analysis'])
    else:
        print(f"Error: {result['error']}")
    
    return result


async def test_performance_analyzer():
    """Test the Performance Analyzer Agent"""
    print("\n" + "=" * 60)
    print("Testing Performance Analyzer Agent")
    print("=" * 60)
    
    print("Creating PerformanceAnalyzerAgent...")
    agent = PerformanceAnalyzerAgent()
    print("✓ Agent created successfully")
    
    print("Calling analyze_code (this may take 10-30 seconds)...")
    result = await agent.analyze_code(
        code=SAMPLE_CODE,
        filename="test_sample.py",
        context={"language": "python", "expected_load": "1000 requests/minute"}
    )
    print("✓ Analysis complete")
    
    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        print(f"Performance issues: {result['issues']}")
        print("\nPerformance Analysis:")
        print("-" * 40)
        print(result['analysis'])
    else:
        print(f"Error: {result['error']}")
    
    return result


async def main():
    """Run all agent tests"""
    print("Starting agent tests...")
    print("This will test all three specialized agents with sample code containing various issues.\n")
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found in environment variables")
        print("Please ensure your .env file contains: OPENAI_API_KEY=your-key-here")
        return
    
    try:
        # Test all agents
        print("Starting Code Reviewer test...")
        code_review_result = await test_code_reviewer()
        
        print("\nStarting Security Checker test...")
        security_result = await test_security_checker()
        
        print("\nStarting Performance Analyzer test...")
        performance_result = await test_performance_analyzer()
        
        # Summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        
        all_success = all([
            code_review_result['status'] == 'success',
            security_result['status'] == 'success',
            performance_result['status'] == 'success'
        ])
        
        if all_success:
            print("✅ All agents tested successfully!")
            print("\nThe sample code contains:")
            print("- Code quality issues (found by Code Reviewer)")
            print("- Security vulnerabilities (found by Security Checker)")
            print("- Performance problems (found by Performance Analyzer)")
            print("\nAgents are ready for integration into the multi-agent system.")
        else:
            print("❌ Some agents failed. Please check the errors above.")
    
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())