#!/usr/bin/python3
# Read current games info and update the database with game info

import argparse
import datetime
from dateutil.relativedelta import *
import errno
import inspect
import json
import string
from lxml import etree
from bs4 import BeautifulSoup
import os
from subprocess import call
import sys
import time
import requests
import requests_cache
import logging
import unidecode

sys.path.insert(1, os.path.abspath('./submodules/streamcamel-py'))
from streamcamel import StreamCamel

logger = logging.getLogger(__name__)

def get_script_dir(follow_symlinks=True):
    if getattr(sys, 'frozen', False): # py2exe, PyInstaller, cx_Freeze
        path = os.path.abspath(sys.executable)
    else:
        path = inspect.getabsfile(get_script_dir)
    if follow_symlinks:
        path = os.path.realpath(path)
    return os.path.dirname(path)

def is_int(s):
    try: 
        int(s)
        return True
    except ValueError:
        return False

def make_dir(dir):
    try:
        os.makedirs(dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

def get_url(url):
    headers =   {
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36 (compatible; YandexScreenshotBot/3.0; +http://yandex.com/bots)'
                }

    response = requests.get(url, headers=headers)
    if not response.from_cache:
        time.sleep(5.0)

    if response.status_code >= 500:
        logging.warning("Url: {} returned error: {}".format(url, response.status_code))

    content = response.content
    return content

def get_game_viewers(game, date):
    base_url = 'https://sullygnome.com/game/' + game + '/'
    date_string = date.strftime("%Y%B").lower()
    url = base_url + date_string

    content = get_url(url)

    soup = BeautifulSoup(content, features="lxml")
    dom = etree.HTML(str(soup))

    if dom is None:
        logging.warning("Game {} for date {} cannot be parsed".format(game, date))
        return -1

    elem = dom.xpath('/html/body/div[2]/div[2]/div[4]/div/div[3]/div/div/div[2]/div')
    if elem is not None:
        for child in elem:
            value = child.text.replace(",", "")
            if is_int(value):
                return int(value)
            else:
                logging.warning("Game {} for date {} doesn't have a parsable viewers count: {}".format(game, date, child.text))
                return -1
    else:
        return -1

def scrape_game(game):
    game_output_dir = 'output/games'
    make_dir(game_output_dir)

    sdate = datetime.date(2015, 8, 1)
    edate = datetime.date.today()

    # SullyGnome returns 0 for the current month
    edate = edate + relativedelta(months = -1)

    game_output = []

    d = sdate
    while (d < edate):
        num_viewers = get_game_viewers(game, d)
        print('Game {} got {} viewers for {}'.format(game, num_viewers, d))

        game_entry = {}
        game_entry['date'] = d.strftime("%Y-%m")
        game_entry['average_viewers'] = num_viewers
        if num_viewers == -1:
            game_entry['error'] = 'HTML Parse Error'

        game_output.append(game_entry)
        d = d + relativedelta(months = 1)

        # Early exit to investigate the issue
        if num_viewers == -1:
            break

    with open(game_output_dir + '/' + game + '.json', 'w') as outfile:
        json.dump(game_output, outfile, indent=4, sort_keys=True)

def normalize_name(game_name):
    normalized_name = game_name
    for char in ":'\"?!%$^&*/\\":
        normalized_name = normalized_name.replace(char, '')

    # Multiple spaces back to 1, and replaced by _
    normalized_name = ' '.join(normalized_name.split())
    normalized_name = normalized_name.replace(' ', '_')

    normalized_name = unidecode.unidecode(normalized_name)

    return normalized_name

def main(args):
    parser = argparse.ArgumentParser(description='GnomeSully Scrapping')
    parser.add_argument("--url", type=str, help="Full game URL to parse")
    parser.add_argument("--game", type=str, help="Game to parse (e.g. Fortnite)")
    parser.add_argument("--streamcamel_games", default=False, action='store_true')
    parser.add_argument("--company", type=str, help="Company's games to parse (e.g. electronic-arts)")

    args = parser.parse_args()
    url = args.url
    game = args.game
    streamcamel_games = args.streamcamel_games
    company = args.company

    make_dir('cache')
    requests_cache.install_cache('cache/cache')
    
    if url is not None:
        content = get_url(url)
        soup = BeautifulSoup(content, features="lxml")
        dom = etree.HTML(str(soup))
        elem = dom.xpath('/html/body/div[2]/div[2]/div[4]/div/div[3]/div/div/div[2]/div')
        for child in elem:
            print(child.text)
    
    if game is not None:
        scrape_game(game)
    
    if streamcamel_games:
        st = StreamCamel()
        games = st.games_stats()

        count = 0
        for game in games:
            count += 1
            game_name = game['name']
            normalized_name = normalize_name(game_name)
            print('[{}/{}] Game={}, normalized={}'.format(count, len(games), game_name, normalized_name))
            scrape_game(normalized_name)

    if company:
        st = StreamCamel()
        games = st.games_stats(company=company)

        count = 0
        for game in games:
            count += 1
            game_name = game['name']
            normalized_name = normalize_name(game_name)
            print('[{}/{}] Game={}, normalized={}'.format(count, len(games), game_name, normalized_name))
            scrape_game(normalized_name)

if __name__ == '__main__':
    logging.basicConfig(level=os.getenv('LOGLEVEL', 'INFO'), stream=sys.stdout, format='%(module)s %(message)s')
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    os.chdir(dname)
    main(sys.argv)
