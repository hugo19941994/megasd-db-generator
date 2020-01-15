import requests
import json
import time
import os

API_KEY = os.environ['IGDB_API_KEY']

# Regions

REGIONS = {
    1: "europe",
    2: "north_america",
    3: "australia",
    4: "new_zealand",
    5: "japan",
    6: "china",
    7: "asia",
    8: "worldwide"
}

# Download genres
response = requests.request("POST", "https://api-v3.igdb.com/genres",
                            headers={'user-key': API_KEY}, data="fields id,name; limit 500; sort id;")
GENRES = {}
for genre in response.json():
    GENRES[genre['id']] = genre['name']


def download(platform, file_name):
    results = []
    offset = 0

    # Download all games
    games = []

    offset = 0
    while True:
        response = requests.request("POST", "https://api-v3.igdb.com/games", headers={
                                    'user-key': API_KEY}, data=f"fields id,genres,name,release_dates,alternative_names; where platforms = [{platform}]; limit 500;offset {offset};")
        offset += 500
        games += response.json()

        if len(response.json()) < 500:
            break

    # Download alternative games
    alternative_names = {}
    alternative_names_ids = set()
    for y in games:
        if 'alternative_names' in y:
            for x in y['alternative_names']:
                alternative_names_ids.add(x)
    alternative_names_ids = list(alternative_names_ids)

    while True:
        ids = alternative_names_ids[:500]
        alternative_names_ids = alternative_names_ids[500:]
        response = requests.request("POST", "https://api-v3.igdb.com/alternative_names", headers={
                                    'user-key': API_KEY}, data=f"fields name; where id = ({', '.join(map(str, ids))}); limit 500;")
        for name in response.json():
            alternative_names[name['id']] = name['name']

        if len(alternative_names_ids) == 0:
            break

    # Download release dates
    release_dates = {}

    offset = 0
    while True:
        response = requests.request("POST", "https://api-v3.igdb.com/release_dates", headers={
                                    'user-key': API_KEY}, data=f"fields id,y,region; where platform = {platform}; limit 500; offset {offset};")
        offset += 500

        resp_json = response.json()
        for date in resp_json:
            date['region'] = REGIONS[date['region']]
            release_dates[date['id']] = date
            del release_dates[date['id']]['id']

        if len(resp_json) < 500:
            break

    # substitute all release_dates and alternative_names
    n_games = []
    for game in games:
        if 'alternative_names' in game:
            names = game['alternative_names']
            game['alternative_names'] = []
            for name in names:
                game['alternative_names'].append(alternative_names[name])

        if 'release_dates' in game:
            dates = game['release_dates']
            game['release_dates'] = []
            for date in dates:
                if date in release_dates:
                    game['release_dates'].append(release_dates[date])

        if 'genres' in game:
            game_genres = game['genres']
            game['genres'] = []
            for genre in game_genres:
                game['genres'].append(convert_genre(GENRES[genre]))

        n_games.append(game)

    with open(f'dbs/{file_name}', 'w') as f:
        json.dump(n_games, f)


def convert_genre(genre):
    genre_conversion = {
        "Point-and-click": "Strategy",
        "Fighting": "Fighter",
        "Shooter": "Shooter",
        "Music": "Other",
        "Platform": "Platform",
        "Puzzle": "Puzzle",
        "Racing": "Sports",
        "Real Time Strategy (RTS)": "Strategy",
        "Role-playing (RPG)": "Strategy",
        "Simulator": "Other",
        "Sport": "Sports",
        "Strategy": "Strategy",
        "Turn-based strategy (TBS)": "Strategy",
        "Tactical": "Strategy",
        "Hack and slash/Beat 'em up": "Beat\'Em-Up",
        "Quiz/Trivia": "Puzzle",
        "Pinball": "Other",
        "Adventure": "Action",
        "Indie": "Other",
        "Arcade": "Action",
        "Visual Novel": "Other",
    }
    return genre_conversion[genre]


if __name__ == "__main__":
    dbs = [(29, 'genesis.json'), (64, 'ms.json'), (78, 'cd.json'), (30, '32x.json'), (84, 'sg1000.json')]

    for db in dbs:
        download(db[0], db[1])
