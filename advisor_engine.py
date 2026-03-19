import requests
from bs4 import BeautifulSoup
from ollama_client import OllamaClient

class TechAdvisor:
    def __init__(self):
        self.ai = OllamaClient()

    def search_resources(self, topic):
        """
        Scrapes Hacker News for relevant GitHub libraries.
        This is the 'Retrieval' part of RAG.
        """
        print(f"🔎 Searching for live resources about: {topic}...")
        
        # We'll scrape Hacker News for GitHub links as our live knowledge base
        search_url = "https://news.ycombinator.com/from?site=github.com"
        
        try:
            response = requests.get(search_url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract links and titles 
            raw_resources = []
            for span in soup.find_all('span', class_='titleline'):
                a_tag = span.find('a')
                if a_tag:
                    raw_resources.append({
                        "title": str(a_tag.text),
                        "url": str(a_tag['href'])
                    })
            
            # Take the top 10 results to feed into the 'Brain'
            raw_resources = raw_resources[:10]
            
            if not raw_resources:
                return "I couldn't find any live results right now. Please check your internet connection."

            print(f"✅ Found {len(raw_resources)} potential resources. Asking AI to pick the best...")

            # Now we 'Augment' the prompt with the real data (The 'AG' in RAG)
            context_text = "\n".join([f"- {r['title']} ({r['url']})" for r in raw_resources])
            
            system_prompt = f"""
            You are a Technical Advisor. I have found the following live resources for the topic: "{topic}".
            
            RESOURCES FROM DEV COMMUNITY:
            {context_text}
            
            TASKS:
            1. Select the top 2 resources that would help someone building this.
            2. Explain WHY they are useful for this specific topic.
            3. Provide the direct links.
            """
            return self.ai.generate_response(system_prompt)

        except Exception as e:
            return f"❌ Scraping Error: {e}"

if __name__ == "__main__":
    advisor = TechAdvisor()
    user_interest = "How to build an AI agent locally on Mac"
    recommendation = advisor.search_resources(user_interest)
    print(f"\n🚀 Recommendation:\n{recommendation}")
