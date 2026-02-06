import requests
import json
from pathlib import Path
from datetime import datetime
import re
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
TRENDS_FILE = OUTPUT_DIR / "trending_topics.json"

# Create output directory if it doesn't exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# YouTube API Configuration
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
if not YOUTUBE_API_KEY:
    raise ValueError("YOUTUBE_API_KEY environment variable not set. Please set it in your .env file.")
BASE_URL = "https://www.googleapis.com/youtube/v3"

print("=== Fetching Gaming Trends from YouTube ===\n")

trending_data = {
    "timestamp": datetime.now().isoformat(),
    "source": "YouTube",
    "trends": {}
}

def extract_game_names(title):
    """Try to extract potential game names from video titles"""
    # Look for quoted game names
    quoted = re.findall(r'"([^"]+)"', title)
    if quoted:
        return quoted
    
    # Look for capitalized words (likely game names)
    capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', title)
    return capitalized[:3]  # Limit to first 3

# 1. Get trending gaming videos
print("1. Fetching trending gaming videos...")
try:
    url = f"{BASE_URL}/videos"
    params = {
        'part': 'snippet,statistics',
        'chart': 'mostPopular',
        'regionCode': 'ES',
        'videoCategoryId': '20',  # Gaming category
        'maxResults': 50,
        'key': YOUTUBE_API_KEY
    }
    
    response = requests.get(url, params=params, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        trending_videos = []
        discovered_games = set()
        
        if 'items' in data:
            for item in data['items']:
                snippet = item['snippet']
                stats = item['statistics']
                
                video_info = {
                    'title': snippet['title'],
                    'channel': snippet['channelTitle'],
                    'views': int(stats.get('viewCount', 0)),
                    'likes': int(stats.get('likeCount', 0)),
                    'video_id': item['id']
                }
                
                trending_videos.append(video_info)
                
                # Extract game names
                games = extract_game_names(snippet['title'])
                for game in games:
                    if len(game) > 3:
                        discovered_games.add(game)
            
            # Sort by views
            trending_videos.sort(key=lambda x: x['views'], reverse=True)
            
            trending_data['trends']['trending_videos'] = trending_videos[:20]
            trending_data['trends']['discovered_games'] = sorted(list(discovered_games))
            
            print(f"   Found {len(trending_videos)} trending videos")
            print(f"   Discovered {len(discovered_games)} potential game names\n")
    else:
        print(f"   Error: Status code {response.status_code}")
        if response.status_code == 403:
            print("   Check your API key and make sure YouTube Data API v3 is enabled\n")
        trending_data['trends']['trending_videos'] = []
        trending_data['trends']['discovered_games'] = []

except Exception as e:
    print(f"   Error: {e}\n")
    trending_data['trends']['trending_videos'] = []
    trending_data['trends']['discovered_games'] = []

# 2. Search for specific gaming keywords
print("2. Searching for popular gaming keywords...")
search_keywords = [
    'videojuegos',
    'gameplay español',
    'trailer juego',
    'lanzamiento juego'
]

all_search_results = []
keyword_games = set()

for keyword in search_keywords:
    try:
        url = f"{BASE_URL}/search"
        params = {
            'part': 'snippet',
            'q': keyword,
            'type': 'video',
            'regionCode': 'ES',
            'relevanceLanguage': 'es',
            'maxResults': 10,
            'order': 'viewCount',
            'publishedAfter': '2026-01-01T00:00:00Z',  # This year
            'key': YOUTUBE_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'items' in data:
                for item in data['items']:
                    snippet = item['snippet']
                    
                    result = {
                        'title': snippet['title'],
                        'channel': snippet['channelTitle'],
                        'keyword': keyword,
                        'video_id': item['id']['videoId']
                    }
                    
                    all_search_results.append(result)
                    
                    # Extract game names
                    games = extract_game_names(snippet['title'])
                    for game in games:
                        if len(game) > 3:
                            keyword_games.add(game)
                
                print(f"   '{keyword}': Found {len(data['items'])} results")
        
    except Exception as e:
        print(f"   Error searching '{keyword}': {e}")

print(f"   Total search results: {len(all_search_results)}\n")

trending_data['trends']['search_results'] = all_search_results
trending_data['trends']['keyword_discovered_games'] = sorted(list(keyword_games))

# 3. Combine all discovered games
print("3. Compiling all discovered games...")
all_games = set()
all_games.update(trending_data['trends']['discovered_games'])
all_games.update(trending_data['trends']['keyword_discovered_games'])

# Filter out common non-game words
exclude_words = ['Gameplay', 'Trailer', 'Review', 'Episode', 'Part', 'Live', 'Stream',
                'Guide', 'Tutorial', 'Tips', 'Tricks', 'Update', 'News', 'Español']

filtered_games = [game for game in all_games if game not in exclude_words and len(game) > 2]

trending_data['trends']['all_discovered_games'] = sorted(filtered_games)
print(f"   Total unique games: {len(filtered_games)}\n")

# Save to JSON
with open(TRENDS_FILE, "w", encoding="utf-8") as f:
    json.dump(trending_data, f, indent=2, ensure_ascii=False)

print(f"✓ Saved trends to: {TRENDS_FILE}")
print("\n=== Summary ===")
print(f"Trending videos: {len(trending_data['trends']['trending_videos'])}")
print(f"Search results: {len(trending_data['trends']['search_results'])}")
print(f"Total discovered games: {len(trending_data['trends']['all_discovered_games'])}")

print("\n=== Top 5 Trending Gaming Videos ===")
for i, video in enumerate(trending_data['trends']['trending_videos'][:5], 1):
    print(f"{i}. [{video['views']:,} views] {video['title'][:70]}...")
    print(f"   by {video['channel']}")
