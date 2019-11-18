import requests
import json
import time
import os

API_KEY = os.environ['GB_API_KEY']

def download(platform, file_name):
    results = []
    offset = 0

    # API pagination. 10 should cover ALL games for each platform
    for i in range(10):
        url = "https://www.giantbomb.com/api/games"
        querystring = {"api_key":API_KEY,"format":"json","field_list":"guid,name","filter":f"platforms:{platform}","offset":offset}
        headers = {
            'Accept': "*/*",
            'Cache-Control': "no-cache",
            'Accept-Encoding': "gzip, deflate",
            'Connection': "keep-alive",
            'cache-control': "no-cache"
        }
        response = requests.request("GET", url, headers=headers, params=querystring)
        response = response.json()
        results = results + response['results']
        offset += 100

    with open(f'dbs/{file_name}', 'w') as f:
        querystring = {"api_key":API_KEY,"format":"json","field_list":"original_release_date,genres,expected_release_year"}
        headers = {
            'Accept': "*/*",
            'Cache-Control': "no-cache",
            'Accept-Encoding': "gzip, deflate",
            'Connection': "keep-alive",
            'cache-control': "no-cache"
        }

        res = {}
        for r in results:
            url = "https://www.giantbomb.com/api/game/" + r['guid']
            response = requests.request("GET", url, headers=headers, params=querystring)
            response = response.json()

            date = response['results']['original_release_date']
            if date is not None:
                date = date[:4]
            elif response['results']['expected_release_year'] is not None:
                date = str(response['results']['expected_release_year'])

            genres = []
            if 'genres' not in response['results']:
                response['results']['genres'] = []
            for genre in response['results']['genres']:
                g = genre['name']
                if g == 'Action':
                    g = 'Action'
                if g == 'Strategy':
                    g = 'Strategy'
                if g == 'Sports':
                    g = 'Sports'
                if g == 'Adventure':
                    g = 'Action'
                elif g == 'Role-Playing':
                    g = 'Strategy'
                elif g == 'Driving/Racing':
                    g = 'Driving'
                elif g == 'Simulation':
                    g = 'Other'
                elif g == 'Educational':
                    g = 'Other'
                elif g == 'Educational':
                    g = 'Other'
                elif g == 'Fighting':
                    g = 'Fighter'
                elif g == 'Wrestling':
                    g = 'Wrestling'
                elif g == 'Shooter':
                    g = 'Shooter'
                elif g == 'Real-Time Strategy':
                    g = 'Strategy'
                elif g == 'Card Game':
                    g = 'Board'
                elif g == 'Trivia/Board Game':
                    g = 'Board'
                elif g == 'Compilation':
                    g = 'Misc'
                elif g == 'MMORPG':
                    g = 'Strategy'
                elif g == 'Minigame Collection':
                    g = 'Misc'
                elif g == 'Puzzle':
                    g = 'Puzzle'
                elif g == 'Music/Rhythm':
                    g = 'Music'
                elif g == 'Boxing':
                    g = 'Boxing'
                elif g == 'Football':
                    g = 'Sports'
                elif g == 'Basketball':
                    g = 'Sports'
                elif g == 'Skateboarding':
                    g = 'Sports'
                elif g == 'Flight Simulator':
                    g = 'Other'
                elif g == 'Tennis':
                    g = 'Tennis'
                elif g == 'Billiards':
                    g = 'Sports'
                elif g == 'Fishing':
                    g = 'Sports'
                elif g == 'Golf':
                    g = 'Sports'
                elif g == 'Bowling':
                    g = 'Sports'
                elif g == 'Pinball':
                    g = 'Other'
                elif g == 'Dual-Joystick Shooter':
                    g = 'Shooter'
                elif g == 'First-Person Shooter':
                    g = 'Shooter'
                elif g == 'Snowboarding/Skiing':
                    g = 'Sports'
                elif g == 'Baseball':
                    g = 'Baseball'
                elif g == 'Light-Gun Shooter':
                    g = 'Shooter'
                elif g == 'Text Adventure':
                    g = 'Adventure'
                elif g == 'Brawler':
                    g = 'Beat\'Em-Up'
                elif g == 'Vehicular Combat':
                    g = 'Action'
                elif g == 'Hockey':
                    g = 'Sports'
                elif g == 'Soccer':
                    g = 'Soccer'
                elif g == 'Platformer':
                    g = 'Platform'
                elif g == 'Track & Field':
                    g = 'Sports'
                elif g == 'Action-Adventure':
                    g = 'Action'
                elif g == 'Fitness':
                    g = 'Sports'
                elif g == 'Block-Breaking':
                    g = 'Other'
                elif g == 'Cricket':
                    g = 'Sports'
                elif g == 'Surfing':
                    g = 'Sports'
                elif g == 'Shoot \'Em Up':
                    g = 'Shooter'
                elif g == 'Gambling':
                    g = 'Other'
                elif g == 'MOBA':
                    g = 'Other'
                genres.append(g)

            res[r['name']] = {'date': date, 'genres': genres}
            print(res[r['name']])
            time.sleep(1)

        json.dump(res, f)

if __name__ == "__main__":
    dbs = [(6, 'md.json'), (8, 'ms.json'), (29, 'scd.json'), (31, '32x.json'), (141, 'sg.json')]

    for db in dbs:
        download(db[0], db[1])


