"""
Aggregate Trending Gaming Topics
==================================
Fetches trending gaming topics from Reddit, Steam, and YouTube,
then combines and scores them to identify the most relevant trends.

Output: Single JSON file with aggregated, deduplicated, and scored trends.
"""

import requests
import json
from pathlib import Path
from datetime import datetime
import re
import os
from dotenv import load_dotenv
from collections import defaultdict

# Load environment variables
load_dotenv()

# Paths
SCRIPT_DIR = Path(__file__).parent.parent.parent
OUTPUT_DIR = SCRIPT_DIR / "output"
TRENDS_FILE = OUTPUT_DIR / "trending_topics.json"

# Create output directory
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Configuration
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def clean_game_name(name):
    """Clean and normalize game names"""
    # Remove brackets and parentheses content
    name = re.sub(r'\[.*?\]', '', name)
    name = re.sub(r'\(.*?\)', '', name)
    
    # Remove common suffixes
    name = re.sub(r'\s*-\s*(Gameplay|Trailer|Review|Guide|Update).*$', '', name, flags=re.IGNORECASE)
    
    # Remove special characters but keep alphanumeric and spaces
    name = re.sub(r'[^\w\s:-]', '', name)
    
    # Clean up whitespace
    name = ' '.join(name.split())
    
    return name.strip()

def is_valid_game_name(name):
    """Filter out non-game names"""
    if len(name) < 3:
        return False
    
    # Exclude common non-game words
    exclude_words = {
        'gameplay', 'trailer', 'review', 'episode', 'part', 'live', 'stream',
        'guide', 'tutorial', 'tips', 'tricks', 'update', 'news', 'español',
        'pc', 'ps5', 'xbox', 'nintendo', 'switch', 'gaming', 'game', 'games',
        'video', 'channel', 'subscribe', 'like', 'comentar'
    }
    
    if name.lower() in exclude_words:
        return False
    
    # Must have at least one letter
    if not re.search(r'[a-zA-Z]', name):
        return False
    
    return True

def extract_game_names_from_text(text):
    """Extract potential game names from text"""
    games = set()
    
    # Look for quoted names
    quoted = re.findall(r'"([^"]+)"', text)
    games.update(quoted)
    
    quoted = re.findall(r"'([^']+)'", text)
    games.update(quoted)
    
    # Look for title case phrases (3+ words)
    title_case = re.findall(r'\b(?:[A-Z][a-z]+\s*){2,}(?:[A-Z][a-z]+)?\b', text)
    games.update(title_case)
    
    # Clean and filter
    cleaned = set()
    for game in games:
        cleaned_name = clean_game_name(game)
        if is_valid_game_name(cleaned_name):
            cleaned.add(cleaned_name)
    
    return cleaned

# ============================================================================
# REDDIT SCRAPER
# ============================================================================

def fetch_reddit_trends():
    """Fetch trending gaming topics from Reddit"""
    print("📱 Fetching from Reddit...")
    
    results = {
        "games": defaultdict(lambda: {"score": 0, "count": 0, "posts": []}),
        "keywords": defaultdict(int),
        "top_posts": []
    }
    
    subreddits = ["gaming", "Games", "pcgaming", "PS5", "xbox", "NintendoSwitch"]
    
    for subreddit in subreddits:
        try:
            url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=25"
            headers = {'User-Agent': 'Gaming Trends Aggregator 2.0'}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'data' in data and 'children' in data['data']:
                    for post in data['data']['children']:
                        post_data = post['data']
                        title = post_data.get('title', '')
                        score = post_data.get('score', 0)
                        
                        # Only consider popular posts
                        if score > 100:
                            # Store top posts
                            results["top_posts"].append({
                                "title": title,
                                "score": score,
                                "subreddit": subreddit,
                                "url": f"https://reddit.com{post_data.get('permalink', '')}"
                            })
                            
                            # Extract game names
                            games = extract_game_names_from_text(title)
                            for game in games:
                                results["games"][game]["score"] += score
                                results["games"][game]["count"] += 1
                                results["games"][game]["posts"].append(title[:100])
                            
                            # Extract keywords
                            words = re.findall(r'\b[a-z]{4,}\b', title.lower())
                            for word in words:
                                if is_valid_game_name(word):
                                    results["keywords"][word] += score
            
            print(f"   ✓ r/{subreddit}")
        
        except Exception as e:
            print(f"   ✗ r/{subreddit}: {e}")
    
    # Sort top posts
    results["top_posts"].sort(key=lambda x: x["score"], reverse=True)
    results["top_posts"] = results["top_posts"][:20]
    
    print(f"   Found {len(results['games'])} games, {len(results['top_posts'])} top posts\n")
    return results

# ============================================================================
# STEAM SCRAPER
# ============================================================================

def fetch_steam_trends():
    """Fetch trending games from Steam"""
    print("🎮 Fetching from Steam...")
    
    results = {
        "games": defaultdict(lambda: {"score": 0, "category": set()}),
        "categories": {
            "top_sellers": [],
            "most_played": [],
            "new_releases": []
        }
    }
    
    try:
        # Get featured categories
        url = "https://store.steampowered.com/api/featuredcategories/?cc=ES&l=spanish"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Top sellers
            if 'top_sellers' in data and 'items' in data['top_sellers']:
                for i, item in enumerate(data['top_sellers']['items'][:15]):
                    name = clean_game_name(item.get('name', ''))
                    if is_valid_game_name(name):
                        score = 100 - (i * 5)  # Higher rank = higher score
                        results["games"][name]["score"] += score
                        results["games"][name]["category"].add("top_seller")
                        results["categories"]["top_sellers"].append(name)
                
                print(f"   ✓ Top sellers: {len(results['categories']['top_sellers'])}")
            
            # New releases
            if 'new_releases' in data and 'items' in data['new_releases']:
                for i, item in enumerate(data['new_releases']['items'][:15]):
                    name = clean_game_name(item.get('name', ''))
                    if is_valid_game_name(name):
                        score = 80 - (i * 4)
                        results["games"][name]["score"] += score
                        results["games"][name]["category"].add("new_release")
                        results["categories"]["new_releases"].append(name)
                
                print(f"   ✓ New releases: {len(results['categories']['new_releases'])}")
        
    except Exception as e:
        print(f"   ✗ Steam API error: {e}")
    
    # Add popular evergreen games (fallback)
    evergreen = {
        "Counter-Strike 2": 150,
        "Dota 2": 140,
        "PUBG": 130,
        "GTA V": 120,
        "Apex Legends": 110,
        "Rust": 100,
        "Palworld": 95,
        "Helldivers 2": 90
    }
    
    for game, score in evergreen.items():
        if game not in results["games"]:
            results["games"][game]["score"] += score
            results["games"][game]["category"].add("popular")
            results["categories"]["most_played"].append(game)
    
    print(f"   ✓ Most played: {len(results['categories']['most_played'])}")
    print(f"   Found {len(results['games'])} unique games\n")
    
    return results

# ============================================================================
# YOUTUBE SCRAPER
# ============================================================================

def fetch_youtube_trends():
    """Fetch trending gaming videos from YouTube"""
    print("📺 Fetching from YouTube...")
    
    results = {
        "games": defaultdict(lambda: {"score": 0, "videos": []}),
        "trending_videos": []
    }
    
    if not YOUTUBE_API_KEY:
        print("   ⚠ YOUTUBE_API_KEY not set, skipping YouTube\n")
        return results
    
    try:
        # Get trending gaming videos
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            'part': 'snippet,statistics',
            'chart': 'mostPopular',
            'regionCode': 'ES',
            'videoCategoryId': '20',  # Gaming
            'maxResults': 50,
            'key': YOUTUBE_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'items' in data:
                for item in data['items']:
                    snippet = item['snippet']
                    stats = item['statistics']
                    title = snippet['title']
                    views = int(stats.get('viewCount', 0))
                    
                    # Store trending video
                    results["trending_videos"].append({
                        "title": title,
                        "channel": snippet['channelTitle'],
                        "views": views,
                        "video_id": item['id']
                    })
                    
                    # Extract game names
                    games = extract_game_names_from_text(title)
                    for game in games:
                        # Score based on views (normalized)
                        score = min(views / 10000, 100)  # Cap at 100
                        results["games"][game]["score"] += score
                        results["games"][game]["videos"].append(title[:80])
                
                print(f"   ✓ Trending videos: {len(results['trending_videos'])}")
        
        elif response.status_code == 403:
            print("   ✗ API quota exceeded or invalid key")
        else:
            print(f"   ✗ HTTP {response.status_code}")
    
    except Exception as e:
        print(f"   ✗ YouTube API error: {e}")
    
    # Sort trending videos
    results["trending_videos"].sort(key=lambda x: x["views"], reverse=True)
    results["trending_videos"] = results["trending_videos"][:20]
    
    print(f"   Found {len(results['games'])} games from videos\n")
    return results

# ============================================================================
# AGGREGATION
# ============================================================================

def aggregate_results(reddit_data, steam_data, youtube_data):
    """Combine and score all results"""
    print("🔄 Aggregating results...\n")
    
    # Combine all games
    all_games = defaultdict(lambda: {
        "score": 0,
        "sources": set(),
        "mentions": 0,
        "reddit_score": 0,
        "steam_score": 0,
        "youtube_score": 0,
        "categories": set(),
        "sample_posts": []
    })
    
    # Add Reddit data
    for game, data in reddit_data["games"].items():
        all_games[game]["score"] += data["score"] * 0.3  # 30% weight
        all_games[game]["reddit_score"] = data["score"]
        all_games[game]["mentions"] += data["count"]
        all_games[game]["sources"].add("Reddit")
        all_games[game]["sample_posts"].extend(data["posts"][:2])
    
    # Add Steam data
    for game, data in steam_data["games"].items():
        all_games[game]["score"] += data["score"] * 0.4  # 40% weight
        all_games[game]["steam_score"] = data["score"]
        all_games[game]["sources"].add("Steam")
        all_games[game]["categories"].update(data["category"])
    
    # Add YouTube data
    for game, data in youtube_data["games"].items():
        all_games[game]["score"] += data["score"] * 0.3  # 30% weight
        all_games[game]["youtube_score"] = data["score"]
        all_games[game]["sources"].add("YouTube")
        all_games[game]["sample_posts"].extend(data["videos"][:2])
    
    # Convert to list and sort
    games_list = []
    for game, data in all_games.items():
        games_list.append({
            "name": game,
            "total_score": round(data["score"], 2),
            "sources": sorted(list(data["sources"])),
            "source_count": len(data["sources"]),
            "mentions": data["mentions"],
            "reddit_score": round(data["reddit_score"], 2),
            "steam_score": round(data["steam_score"], 2),
            "youtube_score": round(data["youtube_score"], 2),
            "categories": sorted(list(data["categories"])),
            "sample_posts": data["sample_posts"][:3]
        })
    
    # Sort by score
    games_list.sort(key=lambda x: x["total_score"], reverse=True)
    
    return games_list

# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("🎮 GAMING TRENDS AGGREGATOR 🎮".center(70))
    print("=" * 70)
    print()
    
    start_time = datetime.now()
    
    # Fetch from all sources
    reddit_data = fetch_reddit_trends()
    steam_data = fetch_steam_trends()
    youtube_data = fetch_youtube_trends()
    
    # Aggregate
    trending_games = aggregate_results(reddit_data, steam_data, youtube_data)
    
    # Create output
    output = {
        "timestamp": start_time.isoformat(),
        "generated_at": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "total_games_found": len(trending_games),
            "multi_source_games": len([g for g in trending_games if g["source_count"] > 1]),
            "reddit_posts": len(reddit_data["top_posts"]),
            "steam_games": len(steam_data["games"]),
            "youtube_videos": len(youtube_data["trending_videos"])
        },
        "top_trending_games": trending_games[:50],  # Top 50
        "raw_data": {
            "reddit_top_posts": reddit_data["top_posts"][:10],
            "youtube_trending_videos": youtube_data["trending_videos"][:10],
            "steam_categories": steam_data["categories"]
        }
    }
    
    # Save to file
    with open(TRENDS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("=" * 70)
    print("✅ SUMMARY".center(70))
    print("=" * 70)
    print(f"Total unique games: {output['summary']['total_games_found']}")
    print(f"Multi-source games: {output['summary']['multi_source_games']}")
    print(f"Reddit posts analyzed: {output['summary']['reddit_posts']}")
    print(f"Steam games tracked: {output['summary']['steam_games']}")
    print(f"YouTube videos analyzed: {output['summary']['youtube_videos']}")
    print()
    print("📊 TOP 15 TRENDING GAMES:")
    print("-" * 70)
    
    for i, game in enumerate(trending_games[:15], 1):
        sources_badge = "".join([
            "🎮" if "Steam" in game["sources"] else "",
            "📱" if "Reddit" in game["sources"] else "",
            "📺" if "YouTube" in game["sources"] else ""
        ])
        
        print(f"{i:2}. {game['name'][:40]:40} {sources_badge} [{game['total_score']:.0f}]")
        if game['categories']:
            print(f"     Tags: {', '.join(game['categories'][:3])}")
    
    print()
    print(f"💾 Saved to: {TRENDS_FILE}")
    print()
    
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"⏱️  Completed in {elapsed:.1f} seconds")
    print("=" * 70)

if __name__ == "__main__":
    main()
