import requests
import logging
import json
import os


class IGDBDownloader():
    def __init__(self):
        logging.info("Downloading info from IGDB\n")

        self.headers = {'Client-ID': os.environ['TWITCH_CLIENT_ID'], 'Authorization': f'Bearer {self.get_token()}'}

        self.genres = self.download_genres()
        self.regions = {
            1: "europe",
            2: "north_america",
            3: "australia",
            4: "new_zealand",
            5: "japan",
            6: "china",
            7: "asia",
            8: "worldwide"
        }

        for db in [(29, 'genesis.json'), (64, 'ms.json'), (78, 'cd.json'), (30, '32x.json'), (84, 'sg1000.json')]:
            self.download_console(db[0], db[1])

        if len(os.listdir("./dbs")) != 5:
            raise Exception("Expected 5 JSONs in ./dbs folder")

    def get_token(self):
        r = requests.request("POST", "https://id.twitch.tv/oauth2/token", params={
            'client_id': os.environ['TWITCH_CLIENT_ID'],
            'client_secret': os.environ['TWITCH_CLIENT_SECRET'],
            'grant_type': 'client_credentials'
        })
        r.raise_for_status()

        return r.json()['access_token']

    def download_genres(self):
        """
        Downloads all IGDB genres
        """

        r = requests.request("POST", "https://api.igdb.com/v4/genres",
                             headers=self.headers,
                             data="fields id,name; limit 500; sort id;")
        r.raise_for_status()

        genres = {}
        for genre in r.json():
            genres[genre['id']] = genre['name']

        return genres

    def download_games(self, platform):
        """
        Downloads all games for a platform
        """
        games = []

        offset = 0
        while True:
            r = requests.request("POST", "https://api.igdb.com/v4/games",
                                 headers=self.headers,
                                 data=f"fields id,genres,name,release_dates,alternative_names; where platforms = [{platform}]; limit 500;offset {offset};")
            r.raise_for_status()
            offset += 500
            games += r.json()

            if len(r.json()) < 500:
                break

        return games

    def download_alternative_names(self, games):
        """
        Downloads the alternative names for each game
        """
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
            r = requests.request("POST", "https://api.igdb.com/v4/alternative_names",
                                 headers=self.headers,
                                 data=f"fields name; where id = ({', '.join(map(str, ids))}); limit 500;")
            r.raise_for_status()

            for name in r.json():
                alternative_names[name['id']] = name['name']

            if len(alternative_names_ids) == 0:
                break

        return alternative_names

    def download_release_dates(self, platform):
        """
        Downloads all release dates for a given platform
        """
        release_dates = {}

        offset = 0
        while True:
            r = requests.request("POST", "https://api.igdb.com/v4/release_dates",
                                 headers=self.headers,
                                 data=f"fields id,y,region; where platform = {platform}; limit 500; offset {offset};")
            r.raise_for_status()
            offset += 500

            resp_json = r.json()
            for date in resp_json:
                # TODO: id 203063 has region 9 for some reason
                date['region'] = self.regions.get(date['region'], 'worldwide')
                release_dates[date['id']] = date
                del release_dates[date['id']]['id']

            if len(resp_json) < 500:
                break

        return release_dates

    def download_console(self, platform, file_name):

        games = self.download_games(platform)
        alternative_names = self.download_alternative_names(games)
        release_dates = self.download_release_dates(platform)

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
                    game['genres'].append(self.convert_genre(self.genres[genre]))

            n_games.append(game)

        if not os.path.exists("./dbs"):
            os.mkdir("./dbs")
        with open(f'dbs/{file_name}', 'w') as f:
            json.dump(n_games, f)

    @staticmethod
    def convert_genre(genre):
        genre_conversion = {
            "Point-and-click": "Strategy",
            "Fighting": "Fighter",
            "Shooter": "Shooter",
            "Music": "Other",
            "Platform": "Platform",
            "Puzzle": "Puzzle",
            "Racing": "Driving",
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
