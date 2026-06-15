from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

def fetch_news(query):
    # TOI Topic Search URL
    # Using /news suffix for a cleaner article list if possible, or just the main topic page
    url = f"https://timesofindia.indiatimes.com/topic/{query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/"
    }

    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code != 200:
            return {"error": f"Failed to fetch articles. Status Code: {res.status_code}", "status": res.status_code}
        
        soup = BeautifulSoup(res.text, "html.parser")
        results = []

        # TOI Topic result cards use the class 'uwU81' for news items
        articles = soup.select('.uwU81')
        
        # Fallback if the class changes or is slightly different
        if not articles:
            # Look for <a> tags containing "/articleshow/" and ending in ".cms"
            articles = [a.find_parent('div') for a in soup.find_all('a', href=True) if '/articleshow/' in a['href'] and a['href'].endswith('.cms')]
            # Eliminate duplicates (parent div could be the same for multiple links)
            seen = set()
            articles = [x for x in articles if x and id(x) not in seen and not seen.add(id(x))]

        for art in articles:
            if not art:
                continue
            
            # 1. Title: Usually in a <span> inside the card
            title_tag = art.find('span')
            if not title_tag:
                 continue
            title = title_tag.get_text(strip=True)
            
            # 2. Link: Find the <a> tag wrapping the card or inside it
            link_tag = art.find('a', href=True)
            if not link_tag:
                continue
            link = link_tag['href']
            if not link.startswith('http'):
                 link = "https://timesofindia.indiatimes.com" + (link if link.startswith('/') else '/' + link)
            
            # 3. Summary: Usually in a <p> or a <div> with a specific structure
            summary_tag = art.find('p')
            if not summary_tag:
                 summary_tag = art.find('div', class_=lambda c: c and 'summary' in c.lower())
            summary = summary_tag.get_text(strip=True) if summary_tag else "No description available."
            
            # 4. Published Date: TOI often uses span.v8un6 for timestamp/source
            time_tag = art.find('span', class_='v8un6')
            if not time_tag:
                time_tag = art.find(['span', 'div'], class_=lambda c: c and ('time' in c.lower() or 'date' in c.lower()))
            published = time_tag.get_text(strip=True) if time_tag else "Unknown Time"
            
            # Filter matches for the ".cms" pattern (optional, but good for validation)
            if '/articleshow/' in link and link.endswith('.cms'):
                results.append({
                    "title": title,
                    "url": link,
                    "summary": summary,
                    "published": published
                })

        # Remove duplicates based on URL
        unique_results = []
        seen_urls = set()
        for r in results:
            if r['url'] not in seen_urls:
                unique_results.append(r)
                seen_urls.add(r['url'])

        return {"results": unique_results}

    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}", "status": 500}
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}", "status": 500}

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    # Process search query for TOI URL (slashes or spaces to hyphens)
    safe_query = query.replace(" ", "-").lower()
    data = fetch_news(safe_query)
    
    if "error" in data:
        return jsonify({"error": data["error"]}), data.get("status", 500)
    
    return jsonify(data["results"])

if __name__ == "__main__":
    app.run(port=5000, debug=True)
