import json
import csv
import os
import random
import requests
import time
import argparse
from datetime import datetime, timedelta
import anthropic
import dotenv
import sys
import re

# Load environment variables
dotenv.load_dotenv()

# Create output directories
def create_directories(platforms):
    for platform in platforms:
        os.makedirs(f"output/{platform}", exist_ok=True)

# Load file generation types
def load_file_generation_types():
    with open('file_generation_types.json', 'r') as f:
        return json.load(f)

# Load themes
def load_themes():
    themes = []
    with open('generation_themes.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            themes.append(row)
    return themes

# Load company profile
def load_company_profile():
    with open('sondermind_company_profile.md', 'r') as f:
        return f.read()

# Generate synthetic data using Claude API
def generate_with_claude(prompt, max_tokens=2500):
    """Generate content using Claude API"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not api_key:
        print("ANTHROPIC_API_KEY not found in environment variables.")
        print("Using placeholder response for demo purposes.")
        return f"[PLACEHOLDER] Synthetic data would be generated based on the prompt."
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        message = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=max_tokens,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return message.content[0].text
    except Exception as e:
        print(f"Error calling Claude API: {e}")
        # Fallback to placeholder for demo purposes
        return f"[API ERROR] Synthetic data would be generated based on the prompt. Error: {str(e)}"

# Clean up LLM-generated content to remove explanatory text
def clean_llm_content(content, format_type):
    # Clean up JSON content
    if format_type == ".json":
        # Try to find and extract just the JSON part
        json_pattern = r'```(?:json)?(.*?)```'
        json_matches = re.findall(json_pattern, content, re.DOTALL)
        
        if json_matches:
            # Take the first JSON match
            return json_matches[0].strip()
        
        # If no JSON block with backticks, try to find content between curly braces
        if content.count('{') >= 1 and content.count('}') >= 1:
            start_idx = content.find('{')
            # Find the last closing brace
            end_idx = content.rfind('}') + 1
            if start_idx < end_idx:
                return content[start_idx:end_idx]
    
    # Clean up Markdown content
    elif format_type == ".md":
        # Remove any markdown code block indicators
        content = re.sub(r'```markdown|```md|```', '', content)
        # Remove explanatory text at the beginning
        content = re.sub(r'^Here\'s a (?:realistic|sample) .*?:\s*', '', content, flags=re.IGNORECASE | re.DOTALL)
    
    # Clean up text content
    elif format_type == ".txt":
        # Remove explanatory text at the beginning
        content = re.sub(r'^Here\'s a (?:simulated|sample) .*?:\s*', '', content, flags=re.IGNORECASE | re.DOTALL)
    
    # General cleanup for all formats
    # Remove "Here's a realistic/sample..." phrases
    content = re.sub(r'^Here\'s a (?:realistic|sample) .*?:\s*', '', content, flags=re.IGNORECASE)
    # Remove trailing "This JSON/document provides..." explanations
    content = re.sub(r'\nThis (?:JSON|document|content) provides.*$', '', content, flags=re.IGNORECASE | re.DOTALL)
    
    return content.strip()

# Extract relevant sections from company profile
def extract_relevant_profile_info(company_profile, section_name=None):
    sections = {
        "overview": company_profile.split("**Overview**")[1].split("**Users**")[0].strip(),
        "users": company_profile.split("**Users**")[1].split("**Competitors**")[0].strip(),
        "competitors": company_profile.split("**Competitors**")[1].split("**Services/Products**")[0].strip(),
        "services": company_profile.split("**Services/Products**")[1].split("**Service Cost Structure**")[0].strip(),
        "costs": company_profile.split("**Service Cost Structure**")[1].split("**User Feedback on SonderMind: Direct Quotes**")[0].strip(),
        "feedback": company_profile.split("**User Feedback on SonderMind: Direct Quotes**")[1].split("**Outreach and Onboarding**")[0].strip(),
        "outreach": company_profile.split("**Outreach and Onboarding**")[1].strip()
    }
    
    if section_name and section_name in sections:
        return sections[section_name]
    return sections

# Generate Coda documents
def generate_coda_files(file_types, themes, company_profile, count=None):
    coda_types = file_types["sondermind_platforms"]["Coda"]
    profile_sections = extract_relevant_profile_info(company_profile)
    
    # If count is specified, randomly select that many file types
    if count and count < len(coda_types):
        coda_types = random.sample(coda_types, count)
    
    for file_type in coda_types:
        # Select 0-4 themes with preference for relevant ones
        doc_type = file_type["type"]
        format_type = file_type["format"]
        
        # Define themes more likely to be relevant for this document type
        relevant_theme_keywords = []
        if "Requirements" in doc_type or "Feature" in doc_type:
            relevant_theme_keywords = ["Feature Requests", "UI", "UX", "Usability", "Pain Points"]
        elif "Feedback" in doc_type:
            relevant_theme_keywords = ["Pain Points", "Objections", "Customer Testimonials", "Usability"]
        elif "Matching" in doc_type or "Intake" in doc_type:
            relevant_theme_keywords = ["Matching Efficiency", "Operational Efficiency", "Engagement", "Platform Stability"]
        elif "Tracking" in doc_type:
            relevant_theme_keywords = ["Operational Efficiency", "Competitive", "Engagement"]
        
        # Filter themes based on relevance (if relevant keywords defined)
        filtered_themes = []
        if relevant_theme_keywords:
            for theme in themes:
                for keyword in relevant_theme_keywords:
                    if keyword in theme['Theme Category'] or keyword in theme['Sub-theme']:
                        filtered_themes.append(theme)
                        break
        
        # If no themes match or no relevant keywords defined, use all themes
        if not filtered_themes:
            filtered_themes = themes
        
        # Randomly decide how many themes to use (0-4)
        num_themes = random.randint(0, 4)
        
        # If num_themes is 0, we'll have an empty list of selected_themes
        selected_themes = random.sample(filtered_themes, min(num_themes, len(filtered_themes))) if num_themes > 0 else []
        
        # Select relevant sections based on document type
        relevant_sections = []
        if "Onboarding" in doc_type:
            relevant_sections = ["overview", "outreach"]
        elif "Match" in doc_type:
            relevant_sections = ["users", "outreach"]
        elif "Roadmap" in doc_type:
            relevant_sections = ["services", "competitors"]
        elif "Billing" in doc_type:
            relevant_sections = ["costs"]
        elif "Feedback" in doc_type:
            relevant_sections = ["feedback"]
        
        # Create specific content for prompt based on document type
        specific_content = ""
        for section in relevant_sections:
            if section in profile_sections:
                specific_content += f"\n--- Relevant Info: {section.upper()} ---\n"
                specific_content += profile_sections[section][:500]  # Truncate to keep prompt reasonable
                specific_content += "\n"
        
        # Create prompt for Claude with natural theme integration instructions
        prompt = f"""
        Generate a realistic {doc_type} for SonderMind in Markdown format. 
        
        About SonderMind:
        SonderMind is a technology-driven behavioral health company that connects individuals with licensed therapists and psychiatrists. 
        They offer both virtual and in-person therapy services with a focus on personalized care. 
        
        {specific_content}
        
        This document should be formatted as a realistic Coda document.
        """
        
        if selected_themes:
            prompt += f"""
            As you create this document, naturally incorporate the following {len(selected_themes)} themes without explicitly labeling them as themes. The content should naturally address these concepts in a way that feels organic to the document:
            """
            
            for theme in selected_themes:
                theme_category = theme['Theme Category']
                subtheme = theme['Sub-theme']
                
                prompt += f"\n- {theme_category}: {subtheme}\n"
                
                # Add specific guidance related to the theme
                if "Pain Points" in subtheme:
                    prompt += "  Naturally include information about challenges therapists face and objections they raise.\n"
                elif "Feature Requests" in subtheme:
                    prompt += "  Incorporate details about features users are requesting and their prioritization.\n"
                elif "Upsell" in subtheme:
                    prompt += "  Include relevant information about premium services and renewal opportunities.\n"
                elif "UX/UI Issues" in subtheme:
                    prompt += "  Address interface problems and improvement recommendations where relevant.\n"
                elif "Competitive" in subtheme:
                    prompt += "  Weave in competitor analysis where it makes sense in the document.\n"
        
        prompt += """
        Please make the content highly specific to SonderMind's business model, using realistic metrics, dates, and terminology.
        Include relevant tables, bullet points, and structured data as would be found in a real document.
        
        IMPORTANT:
        - The document should feel like a cohesive, realistic business document, not a collection of themes
        - Don't use section headings that directly reference the themes unless it would naturally occur in this type of document
        - Don't label or call out the themes explicitly - they should be naturally woven into the content
        - The document's organization and structure should follow standard practices for this document type
        
        IMPORTANT: Do not include any explanatory text like "Here's a realistic document" or "This document provides..." 
        Just give me the document content directly.
        """
        
        print(f"Generating {doc_type}...")
        # Generate content with Claude
        content = generate_with_claude(prompt)
        
        # Clean up the content
        content = clean_llm_content(content, format_type)
        
        # Save to file
        filename = f"output/Coda/{doc_type.replace(' ', '_').lower()}{format_type}"
        with open(filename, 'w') as f:
            f.write(content)
        
        print(f"Generated: {filename}")

# Generate Dialpad data
def generate_dialpad_files(file_types, themes, company_profile, count=None):
    dialpad_types = file_types["sondermind_platforms"]["Dialpad"]
    profile_sections = extract_relevant_profile_info(company_profile)
    
    # If count is specified, randomly select that many file types
    if count and count < len(dialpad_types):
        dialpad_types = random.sample(dialpad_types, count)
    
    for file_type in dialpad_types:
        # Select 0-4 themes with preference for relevant ones
        doc_type = file_type["type"]
        format_type = file_type["format"]
        
        # Define themes more likely to be relevant for this document type
        relevant_theme_keywords = []
        if "Call Logs" in doc_type or "Outreach" in doc_type:
            relevant_theme_keywords = ["Sales", "Pain Points", "Objections", "Competitive"]
        elif "Objection" in doc_type:
            relevant_theme_keywords = ["Pain Points", "Objections", "Competitive", "Value Proposition"]
        elif "Support" in doc_type:
            relevant_theme_keywords = ["Support Ticket", "Usability", "Feature Requests"]
        elif "Quality" in doc_type:
            relevant_theme_keywords = ["Value Proposition", "Usability", "Operational Efficiency"]
        
        # Filter themes based on relevance
        filtered_themes = []
        if relevant_theme_keywords:
            for theme in themes:
                for keyword in relevant_theme_keywords:
                    if keyword in theme['Theme Category'] or keyword in theme['Sub-theme']:
                        filtered_themes.append(theme)
                        break
        
        # If no themes match or no relevant keywords defined, use all themes
        if not filtered_themes:
            filtered_themes = themes
        
        # Randomly decide how many themes to use (0-4)
        num_themes = random.randint(0, 4)
        
        # If num_themes is 0, we'll have an empty list of selected_themes
        selected_themes = random.sample(filtered_themes, min(num_themes, len(filtered_themes))) if num_themes > 0 else []
        
        # Select relevant sections based on document type
        relevant_sections = []
        if "Call Logs" in doc_type:
            relevant_sections = ["users", "feedback"]
        elif "Conversation" in doc_type:
            relevant_sections = ["feedback", "users"]
        elif "Support" in doc_type:
            relevant_sections = ["feedback", "services"]
        elif "Quality" in doc_type:
            relevant_sections = ["outreach", "feedback"]
        elif "Outreach" in doc_type:
            relevant_sections = ["outreach", "users"]
        
        # Create specific content for prompt
        specific_content = ""
        for section in relevant_sections:
            if section in profile_sections:
                specific_content += f"\n--- Relevant Info: {section.upper()} ---\n"
                specific_content += profile_sections[section][:500]  # Truncate to keep prompt reasonable
                specific_content += "\n"
        
        # Create prompt for Claude with exact Dialpad JSON structure
        prompt = f"""
        Generate a realistic {doc_type} for SonderMind in JSON format.
        
        About SonderMind:
        SonderMind is a technology-driven behavioral health company that connects individuals with licensed therapists and psychiatrists. 
        They offer both virtual and in-person therapy services with a focus on personalized care.
        
        {specific_content}
        
        This document should be formatted as a realistic Dialpad JSON export with the following EXACT structure:
        
        {{
          "call_id": "unique ID string",
          "lines": [
            {{
              "contact_id": "contact ID string",
              "content": "Message content",
              "name": "Speaker name",
              "time": "ISO timestamp format (YYYY-MM-DDThh:mm:ss.ssssss)",
              "type": "transcript"
            }},
            {{
              "content": "action_item or other moment type",
              "name": "Speaker name",
              "time": "ISO timestamp format (YYYY-MM-DDThh:mm:ss.ssssss)",
              "type": "moment",
              "user_id": "user ID string"
            }}
            // And so on with more lines...
          ]
        }}
        
        IMPORTANT REQUIREMENTS:
        1. Each line in the "lines" array must be either:
           - "type": "transcript" (for spoken dialog)
           - "type": "moment" (for system events, action items, etc.)
        2. "transcript" type lines should have: contact_id, content, name, time, type
        3. "moment" type lines should have: content, name, time, type, user_id
        4. "time" values should be valid ISO timestamps in YYYY-MM-DDThh:mm:ss.ssssss format
        5. Caller/therapist exchanges should be realistic for a SonderMind conversation
        """
        
        if selected_themes:
            prompt += f"""
            As you create this JSON document, naturally incorporate the following {len(selected_themes)} themes without explicitly labeling them. The data should naturally include information relevant to these concepts:
            """
            
            for theme in selected_themes:
                theme_category = theme['Theme Category']
                subtheme = theme['Sub-theme']
                
                prompt += f"\n- {theme_category}: {subtheme}\n"
                
                # Add specific guidance related to the theme
                if "Pain Points" in subtheme:
                    prompt += "  Include data about challenges therapists face in conversation content and summary fields.\n"
                elif "Feature Requests" in subtheme:
                    prompt += "  Incorporate feature request mentions and indicators in the data where relevant.\n"
                elif "Upsell" in subtheme:
                    prompt += "  Include data relating to renewal and premium service opportunities where appropriate.\n"
                elif "UX/UI Issues" in subtheme:
                    prompt += "  Incorporate interface issues in conversation content where natural.\n"
                elif "Competitive" in subtheme:
                    prompt += "  Include competitor mentions where they would naturally occur in conversations or data.\n"
        
        prompt += """
        Please make the content highly specific to SonderMind's business model, using realistic dialog, dates, and context.
        
        IMPORTANT:
        - FOLLOW THE EXACT JSON STRUCTURE DEFINED ABOVE
        - The conversation should flow naturally between SonderMind representatives and therapists/clients
        - Create a realistic mix of transcript and moment types throughout
        - Ensure the themes are incorporated naturally in conversation content, not as artificial fields
        - Do not add any additional fields to the JSON structure
        - Make sure all JSON is properly formatted and valid
        
        IMPORTANT: Do not include any explanatory text like "Here's a realistic document" or "This JSON provides..." 
        Just give me the JSON content directly.
        """
        
        print(f"Generating {doc_type}...")
        # Generate content with Claude
        content = generate_with_claude(prompt)
        
        # Clean up the content
        content = clean_llm_content(content, format_type)
        
        # Save to file
        filename = f"output/Dialpad/{doc_type.replace(' ', '_').lower()}{format_type}"
        with open(filename, 'w') as f:
            f.write(content)
        
        print(f"Generated: {filename}")

# Generate Slack data
def generate_slack_files(file_types, themes, company_profile, count=None):
    slack_types = file_types["sondermind_platforms"]["Slack"]
    profile_sections = extract_relevant_profile_info(company_profile)
    
    # If count is specified, randomly select that many file types
    if count and count < len(slack_types):
        slack_types = random.sample(slack_types, count)
    
    for file_type in slack_types:
        # Select 0-4 themes with preference for relevant ones
        doc_type = file_type["type"]
        format_type = file_type["format"]
        
        # Define themes more likely to be relevant for this document type
        relevant_theme_keywords = []
        if "Onboarding" in doc_type:
            relevant_theme_keywords = ["Engagement", "Drop-off", "Operational Efficiency"]
        elif "Matching" in doc_type:
            relevant_theme_keywords = ["Matching", "Efficiency", "Platform Stability"]
        elif "Billing" in doc_type:
            relevant_theme_keywords = ["Pain Points", "Objections", "Support Ticket"]
        elif "Support" in doc_type or "Incident" in doc_type:
            relevant_theme_keywords = ["Platform Stability", "Downtime", "Support Ticket", "UX/UI Issues"]
        elif "Release" in doc_type:
            relevant_theme_keywords = ["Feature Requests", "Competitive", "Usability"]
        
        # Filter themes based on relevance
        filtered_themes = []
        if relevant_theme_keywords:
            for theme in themes:
                for keyword in relevant_theme_keywords:
                    if keyword in theme['Theme Category'] or keyword in theme['Sub-theme']:
                        filtered_themes.append(theme)
                        break
        
        # If no themes match or no relevant keywords defined, use all themes
        if not filtered_themes:
            filtered_themes = themes
        
        # Randomly decide how many themes to use (0-4)
        num_themes = random.randint(0, 4)
        
        # If num_themes is 0, we'll have an empty list of selected_themes
        selected_themes = random.sample(filtered_themes, min(num_themes, len(filtered_themes))) if num_themes > 0 else []
        
        # Select relevant sections based on document type
        relevant_sections = []
        if "Onboarding" in doc_type:
            relevant_sections = ["outreach", "users"]
        elif "Matching" in doc_type:
            relevant_sections = ["users", "services"]
        elif "Billing" in doc_type:
            relevant_sections = ["costs", "feedback"]
        elif "Support" in doc_type:
            relevant_sections = ["feedback", "services"]
        elif "Release" in doc_type:
            relevant_sections = ["services", "competitors"]
        
        # Create specific content for prompt
        specific_content = ""
        for section in relevant_sections:
            if section in profile_sections:
                specific_content += f"\n--- Relevant Info: {section.upper()} ---\n"
                specific_content += profile_sections[section][:500]  # Truncate to keep prompt reasonable
                specific_content += "\n"
        
        # Create prompt for Claude with natural theme incorporation
        prompt = f"""
        Generate a realistic {doc_type} for SonderMind.
        
        About SonderMind:
        SonderMind is a technology-driven behavioral health company that connects individuals with licensed therapists and psychiatrists. 
        They offer both virtual and in-person therapy services with a focus on personalized care.
        
        {specific_content}
        
        This document should be formatted as realistic Slack messages or notifications.
        """
        
        if selected_themes:
            prompt += f"""
            As you create these Slack messages, naturally incorporate the following {len(selected_themes)} themes without explicitly labeling them. The conversation should naturally touch on these topics:
            """
            
            for theme in selected_themes:
                theme_category = theme['Theme Category']
                subtheme = theme['Sub-theme']
                
                prompt += f"\n- {theme_category}: {subtheme}\n"
                
                # Add specific guidance related to the theme
                if "Pain Points" in subtheme:
                    prompt += "  Include messages that discuss challenges therapists face in a natural way.\n"
                elif "Feature Requests" in subtheme:
                    prompt += "  Include mentions of feature requests and prioritization in the conversation.\n"
                elif "Upsell" in subtheme:
                    prompt += "  Incorporate discussion of premium services or renewals where it fits naturally.\n"
                elif "UX/UI Issues" in subtheme:
                    prompt += "  Include messages about interface issues where they would naturally come up.\n"
                elif "Competitive" in subtheme:
                    prompt += "  Incorporate messages mentioning competitors where relevant to the conversation.\n"
        
        # Format the output structure based on the format type
        if format_type == ".json":
            prompt += """
            Please format the output as a JSON array of slack messages with the following structure:
            
            [
              {
                "user": "User's name or bot name",
                "timestamp": "ISO timestamp",
                "text": "Message content",
                "channel": "Channel name",
                "reactions": [
                  {
                    "name": "reaction emoji name",
                    "count": number of reactions,
                    "users": ["user1", "user2"]
                  }
                ],
                "thread_ts": "thread timestamp if part of a thread",
                "replies": [
                  {
                    "user": "Replying user name",
                    "timestamp": "ISO timestamp",
                    "text": "Reply content"
                  }
                ]
              }
            ]
            
            IMPORTANT:
            - The conversation should feel natural and authentic, not contrived around themes
            - Don't explicitly label or flag themes in the messages
            - The selected themes should emerge organically through the conversation topics
            - The message structure should follow realistic Slack conversation patterns
            
            IMPORTANT: Do not include any explanatory text like "Here's a realistic document" or "This JSON provides..." 
            Just give me the JSON content directly.
            """
        else:
            prompt += """
            Please format the output as plain text Slack messages with the following structure:
            
            [Channel: #channel-name]
            
            [User Name] 10:15 AM
            Message content
            
            [Another User] 10:17 AM
            Reply message
            
            [Bot Name] 10:20 AM
            Bot notification or message
            
            IMPORTANT:
            - The conversation should feel natural and authentic, not contrived around themes
            - Don't explicitly label or flag themes in the messages
            - The selected themes should emerge organically through the conversation topics
            - The message structure should follow realistic Slack conversation patterns
            
            IMPORTANT: Do not include any explanatory text like "Here's a realistic document" or "This data provides..." 
            Just give me the Slack message content directly.
            """
        
        print(f"Generating {doc_type}...")
        # Generate content with Claude
        content = generate_with_claude(prompt)
        
        # Clean up the content
        content = clean_llm_content(content, format_type)
        
        # Save to file
        filename = f"output/Slack/{doc_type.replace(' ', '_').lower()}{format_type}"
        with open(filename, 'w') as f:
            f.write(content)
        
        print(f"Generated: {filename}")

def parse_arguments():
    parser = argparse.ArgumentParser(description='Generate synthetic data files for SonderMind platforms')
    
    parser.add_argument('--platforms', '-p', nargs='+', choices=['Coda', 'Dialpad', 'Slack', 'all'],
                        default=['all'], help='Platforms to generate data for (default: all)')
    
    parser.add_argument('--count', '-c', type=int,
                        help='Number of files to generate per platform (default: all available types)')
    
    return parser.parse_args()

def main():
    # Parse command line arguments first
    args = parse_arguments()
    
    # Determine which platforms to generate data for
    if 'all' in args.platforms:
        platforms = ['Coda', 'Dialpad', 'Slack']
    else:
        platforms = args.platforms
    
    # Set up required directories
    create_directories(platforms)
    
    # Load necessary data
    file_types = load_file_generation_types()
    themes = load_themes()
    company_profile = load_company_profile()
    
    try:
        # Generate files for each platform
        if 'Coda' in platforms:
            generate_coda_files(file_types, themes, company_profile, args.count)
            
        if 'Dialpad' in platforms:
            generate_dialpad_files(file_types, themes, company_profile, args.count)
            
        if 'Slack' in platforms:
            generate_slack_files(file_types, themes, company_profile, args.count)
            
        print("\nAll files generated successfully!")
            
    except Exception as e:
        print(f"Error generating files: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    main() 