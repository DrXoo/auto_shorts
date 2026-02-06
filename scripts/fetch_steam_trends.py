import requests
import json
from pathlib import Path
from datetime import datetime

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
TRENDS_FILE = OUTPUT_DIR / "trending_topics.json"

# Create output directory if it doesn't exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=== Fetching Gaming Trends from Steam API ===\n")

trending_data = {
    "timestamp": datetime.now().isoformat(),
    "source": "Steam",
    "trends": {}
}

# 1. Get top sellers from Steam
print("1. Fetching top sellers...")
try:
    # Steam Store API - Featured games (includes top sellers)
    url = "https://store.steampowered.com/api/featuredcategories/?cc=ES&l=spanish"
    response = requests.get(url, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        
        # Get top sellers
        top_sellers = []
        if 'top_sellers' in data and 'items' in data['top_sellers']:
            for item in data['top_sellers']['items'][:10]:
                game_info = {
                    "name": item.get('name', 'Unknown'),
                    "appid": item.get('id'),
                    "discount": item.get('discount_percent', 0)
                }
                top_sellers.append(game_info)
                print(f"   - {game_info['name']}")
        
        trending_data["trends"]["top_sellers"] = top_sellers
        print(f"   Total: {len(top_sellers)} games\n")
    else:
        print(f"   Error: Status code {response.status_code}\n")
        trending_data["trends"]["top_sellers"] = []
except Exception as e:
    print(f"   Error: {e}\n")
    trending_data["trends"]["top_sellers"] = []

# 2. Get most played games
print("2. Fetching most played games...")
try:
    # Steam Spy API alternative - using Steam Charts data
    # Note: This gets top games by player count
    url = "https://api.steampowered.com/ISteamChartsService/GetMostPlayedGames/v1/"
    response = requests.get(url, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        most_played = []
        
        if 'response' in data and 'ranks' in data['response']:
            for rank_data in data['response']['ranks'][:15]:
                appid = rank_data.get('appid')
                
                # Get game name from Steam store API
                try:
                    game_url = f"https://store.steampowered.com/api/appdetails?appids={appid}&cc=ES&l=spanish"
                    game_response = requests.get(game_url, timeout=5)
                    
                    if game_response.status_code == 200:
                        game_data = game_response.json()
                        if str(appid) in game_data and game_data[str(appid)]['success']:
                            game_name = game_data[str(appid)]['data']['name']
                            most_played.append({
                                "name": game_name,
                                "appid": appid,
                                "rank": rank_data.get('rank')
                            })
                            print(f"   - #{rank_data.get('rank')}: {game_name}")
                except Exception:
                    pass
        
        trending_data["trends"]["most_played"] = most_played
        print(f"   Total: {len(most_played)} games\n")
    else:
        print("   Using fallback method...\n")
        # Fallback: Known popular games on Steam
        fallback_games = [
            {"name": "Counter-Strike 2", "appid": 730},
            {"name": "Dota 2", "appid": 570},
            {"name": "PUBG", "appid": 578080},
            {"name": "Apex Legends", "appid": 1172470},
            {"name": "GTA V", "appid": 271590},
            {"name": "Team Fortress 2", "appid": 440},
            {"name": "Rust", "appid": 252490},
            {"name": "ARK", "appid": 346110}
        ]
        trending_data["trends"]["most_played"] = fallback_games
        for game in fallback_games:
            print(f"   - {game['name']}")
        print()
except Exception as e:
    print(f"   Error: {e}\n")
    trending_data["trends"]["most_played"] = []

# 3. Get new releases
print("3. Fetching new and trending releases...")
try:
    url = "https://store.steampowered.com/api/featuredcategories/?cc=ES&l=spanish"
    response = requests.get(url, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        
        # Get new releases
        new_releases = []
        if 'new_releases' in data and 'items' in data['new_releases']:
            for item in data['new_releases']['items'][:10]:
                game_info = {
                    "name": item.get('name', 'Unknown'),
                    "appid": item.get('id')
                }
                new_releases.append(game_info)
                print(f"   - {game_info['name']}")
        
        trending_data["trends"]["new_releases"] = new_releases
        print(f"   Total: {len(new_releases)} games\n")
    else:
        print(f"   Error: Status code {response.status_code}\n")
        trending_data["trends"]["new_releases"] = []
except Exception as e:
    print(f"   Error: {e}\n")
    trending_data["trends"]["new_releases"] = []

# 4. Compile all unique game names for easy searching
print("4. Compiling unique game names...")
all_games = set()

for game in trending_data["trends"]["top_sellers"]:
    all_games.add(game["name"])

for game in trending_data["trends"]["most_played"]:
    all_games.add(game["name"])

for game in trending_data["trends"]["new_releases"]:
    all_games.add(game["name"])

trending_data["trends"]["all_trending_games"] = sorted(list(all_games))
print(f"   Total unique games: {len(all_games)}\n")

# Save to JSON
with open(TRENDS_FILE, "w", encoding="utf-8") as f:
    json.dump(trending_data, f, indent=2, ensure_ascii=False)

print(f"✓ Saved trends to: {TRENDS_FILE}")
print("\n=== Summary ===")
print(f"Top sellers: {len(trending_data['trends']['top_sellers'])}")
print(f"Most played: {len(trending_data['trends']['most_played'])}")
print(f"New releases: {len(trending_data['trends']['new_releases'])}")
print(f"Total unique games: {len(trending_data['trends']['all_trending_games'])}")
