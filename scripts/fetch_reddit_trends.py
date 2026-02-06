import requests
import json
from pathlib import Path
from datetime import datetime
import re

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
TRENDS_FILE = OUTPUT_DIR / "trending_topics.json"

# Create output directory if it doesn't exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=== Fetching Gaming Trends from Reddit ===\n")

trending_data = {
    "timestamp": datetime.now().isoformat(),
    "source": "Reddit",
    "trends": {}
}

# Gaming subreddits to scrape
subreddits = [
    "gaming",
    "Games",
    "pcgaming",
    "PS5",
    "xbox"
]

# Common game-related words to help identify game names
game_indicators = ['trailer', 'gameplay', 'review', 'release', 'announced', 'update', 
                   'patch', 'dlc', 'expansion', 'gameplay', 'screenshots']

def extract_game_names(title):
    """Try to extract potential game names from post titles"""
    # Remove common prefixes
    title = re.sub(r'\[.*?\]', '', title)  # Remove [tags]
    title = re.sub(r'\(.*?\)', '', title)  # Remove (parentheses)
    
    # Look for quoted game names
    quoted = re.findall(r'"([^"]+)"', title)
    if quoted:
        return quoted
    
    quoted = re.findall(r"'([^']+)'", title)
    if quoted:
        return quoted
    
    return []

all_posts = []
discovered_games = set()

# Fetch hot posts from each subreddit
for subreddit in subreddits:
    print(f"Fetching from r/{subreddit}...")
    
    try:
        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=25"
        headers = {'User-Agent': 'Gaming Trends Scraper 1.0'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            posts_count = 0
            
            if 'data' in data and 'children' in data['data']:
                for post in data['data']['children']:
                    post_data = post['data']
                    title = post_data.get('title', '')
                    score = post_data.get('score', 0)
                    num_comments = post_data.get('num_comments', 0)
                    
                    # Only include posts with decent engagement
                    if score > 100:
                        all_posts.append({
                            'title': title,
                            'score': score,
                            'comments': num_comments,
                            'subreddit': subreddit,
                            'url': f"https://reddit.com{post_data.get('permalink', '')}"
                        })
                        
                        # Try to extract game names
                        game_names = extract_game_names(title)
                        for game in game_names:
                            if len(game) > 3:  # Avoid acronyms that are too short
                                discovered_games.add(game)
                        
                        posts_count += 1
            
            print(f"   Found {posts_count} trending posts\n")
        else:
            print(f"   Error: Status code {response.status_code}\n")
    
    except Exception as e:
        print(f"   Error: {e}\n")

# Sort posts by score
all_posts.sort(key=lambda x: x['score'], reverse=True)

# Get top posts
trending_data["trends"]["top_posts"] = all_posts[:20]
trending_data["trends"]["discovered_games"] = sorted(list(discovered_games))

# Extract trending topics from titles
print("Analyzing trending topics...")
word_freq = {}

for post in all_posts:
    title = post['title'].lower()
    # Remove common words
    words = re.findall(r'\b[a-z]{4,}\b', title)
    
    for word in words:
        if word not in ['game', 'games', 'gaming', 'with', 'that', 'this', 'from', 
                       'have', 'been', 'will', 'about', 'what', 'does', 'when']:
            word_freq[word] = word_freq.get(word, 0) + post['score']

# Get top trending words
trending_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]
trending_data["trends"]["trending_keywords"] = [word for word, _ in trending_words]

print(f"   Top trending keywords: {', '.join(trending_data['trends']['trending_keywords'][:10])}\n")

# Save to JSON
with open(TRENDS_FILE, "w", encoding="utf-8") as f:
    json.dump(trending_data, f, indent=2, ensure_ascii=False)

print(f"✓ Saved trends to: {TRENDS_FILE}")
print("\n=== Summary ===")
print(f"Total posts analyzed: {len(all_posts)}")
print(f"Top trending posts saved: {len(trending_data['trends']['top_posts'])}")
print(f"Discovered game names: {len(trending_data['trends']['discovered_games'])}")
print(f"Trending keywords: {len(trending_data['trends']['trending_keywords'])}")

print("\n=== Top 5 Trending Posts ===")
for i, post in enumerate(trending_data['trends']['top_posts'][:5], 1):
    print(f"{i}. [{post['score']}↑] {post['title'][:80]}...")
