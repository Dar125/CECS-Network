#!/usr/bin/env python3
"""
Test script for the Simplified Multi-Agent Orchestrator
"""

import asyncio
import os
from dotenv import load_dotenv
from orchestrator import SimpleMultiAgentOrchestrator

# Load environment variables
load_dotenv()

# Sample code with various issues
SAMPLE_CODE = """
import requests
import pickle

def fetch_user_data(user_id, api_key):
    # Hardcoded URL - security issue
    base_url = "http://api.example.com/users/"
    
    # String concatenation for URL - potential injection
    url = base_url + str(user_id)
    
    # API key in URL - security issue
    response = requests.get(url + "?api_key=" + api_key)
    
    # No error handling
    data = response.json()
    
    # Inefficient: Loading all users to find one
    all_users = data['all_users']
    target_user = None
    for user in all_users:  # O(n) search
        if user['id'] == user_id:
            target_user = user
            break
    
    # Unsafe deserialization
    if target_user and 'profile' in target_user:
        target_user['profile'] = pickle.loads(target_user['profile'])
    
    # Nested loops - O(n²) complexity
    for i in range(len(all_users)):
        for j in range(len(all_users)):
            if i != j and all_users[i]['email'] == all_users[j]['email']:
                print(f"Duplicate email found: {all_users[i]['email']}")
    
    return target_user
"""


async def test_orchestrator():
    """Test the simplified orchestrator"""
    print("="*80)
    print("Testing Simplified Multi-Agent Orchestrator")
    print("="*80)
    
    orchestrator = SimpleMultiAgentOrchestrator()
    
    result = await orchestrator.review_code(
        code=SAMPLE_CODE,
        filename="fetch_user_data.py",
        pr_description="Added user data fetching functionality with API integration",
        context={"language": "python"}
    )
    
    print("\n" + "="*60)
    print("Review Results:")
    print("="*60)
    
    if result['status'] == 'success':
        print(f"\nFile: {result['filename']}")
        print(f"Status: SUCCESS")
        
        # Show consensus results
        consensus = result.get('consensus_results', {})
        recommendations = consensus.get('recommendations', [])
        
        print(f"\nTotal Recommendations: {len(recommendations)}")
        print(f"Agreement Level: {consensus.get('agreement_level', 0)*100:.1f}%")
        
        # Show top recommendations
        if recommendations:
            print("\nTop Recommendations (by consensus score):")
            print("-" * 60)
            for i, rec in enumerate(recommendations[:5], 1):
                print(f"\n{i}. {rec.get('description', 'N/A')}")
                print(f"   Severity: {rec.get('consensus_severity', 'N/A').upper()}")
                print(f"   Score: {rec.get('consensus_score', 0):.1f}")
                print(f"   Agents: {', '.join(rec.get('contributing_agents', []))}")
        
        # Save the markdown report
        report = result.get('markdown_report', '')
        if report:
            with open('sample_review_report.md', 'w') as f:
                f.write(report)
            print("\n✅ Full markdown report saved to: sample_review_report.md")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")
    
    return result


async def main():
    """Run orchestrator test"""
    print("Starting Simplified Multi-Agent Orchestrator Test")
    print("This version directly calls each agent without RoundRobinGroupChat.\n")
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found in environment variables")
        return
    
    try:
        result = await test_orchestrator()
        
        print("\n" + "="*80)
        print("✅ Orchestrator test completed!")
        print("="*80)
        
        if result['status'] == 'success':
            print("\nThe orchestrator successfully:")
            print("- Ran all three specialized agents independently")
            print("- Applied weighted consensus mechanism")
            print("- Generated a unified markdown report")
            print("- Prioritized recommendations by severity and agent agreement")
            print("\nCheck 'sample_review_report.md' for the full report.")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())