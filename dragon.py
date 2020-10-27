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

mapping = {}

def read_mapping():
    with open('config/mapping.json', 'r') as infile:
        container = json.load(infile)
        for entry in container:
            if 'name' in entry and 'normalized' in entry:
                mapping[entry['name']] = entry['normalized']
            else:
                logger.fatal('Mal-formed mapping.json file')
                exit(2)

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

def parse_dom_value(dom, xpath):
    elem = dom.xpath(xpath)
    if elem is not None:
        for child in elem:
            value = child.text.replace(",", "")
            if is_int(value):
                return int(value)
            else:
                return None
    else:
        return None

def get_game_information(game, date):
    base_url = 'https://sullygnome.com/game/' + game + '/'
    date_string = date.strftime("%Y%B").lower()
    url = base_url + date_string

    content = get_url(url)

    soup = BeautifulSoup(content, features="lxml")
    dom = etree.HTML(str(soup))

    if dom is None:
        logging.warning("Game {} for date {} cannot be parsed".format(game, date))
        return (None, None, None)
                                            
    average_viewers = parse_dom_value(dom, '/html/body/div[2]/div[2]/div[4]/div/div[3]/div/div/div[2]/div')
    average_channels = parse_dom_value(dom, '/html/body/div[2]/div[2]/div[4]/div/div[4]/div/div/div[2]/div')
    peak_viewers = parse_dom_value(dom, '/html/body/div[2]/div[2]/div[4]/div/div[6]/div/div/div[2]/div')

    return (average_viewers, average_channels, peak_viewers)


def scrape_game(game_name, game_id=None, skip_existing=False):
    normalized_name = normalize_name(game_name)
    #print('Game={}, normalized={}'.format(game_name, normalized_name))

    game_output_dir = 'output/games'
    make_dir(game_output_dir)

    if skip_existing:
        file_path = game_output_dir + '/' + normalized_name + '.json'
        if os.path.exists(file_path):
            with open(file_path, 'r') as infile:
                container = json.load(infile)
                if 'data' in container:
                    found_error = False
                    for d in container['data']:
                        if 'error' in d:
                            found_error = True
                            break

                    if not found_error:
                        return
                

    sdate = datetime.date(2015, 8, 1)
    edate = datetime.date.today()

    # SullyGnome returns 0 for the current month
    edate = edate + relativedelta(months = -1)

    game_output = {}
    game_output['data'] = []
    game_output['meta-data'] = {
        'streamcamel_name' : game_name,
        'sullygnome_name' : normalized_name,
    }

    if not game_id is None:
        game_output['meta-data']['game_id'] = game_id

    d = sdate
    while (d < edate):
        (num_viewers, num_streams, peak_viewers) = get_game_information(normalized_name, d)
        print('Game {}, viewers={}, streams={}, peak_viewers={}, for {}'.format(
            game_name, num_viewers, num_streams, peak_viewers, d))

        game_entry = {}
        game_entry['date'] = d.strftime("%Y-%m")
        if num_viewers is None or num_streams is None or peak_viewers is None:
            game_entry['error'] = 'HTML Parse Error'
        else:
            game_entry['average_viewers'] = num_viewers
            game_entry['average_channels'] = num_streams
            game_entry['peak_viewers'] = peak_viewers

        game_output['data'].append(game_entry)
        d = d + relativedelta(months = 1)

        # Early exit to investigate the issue
        if num_viewers is None or num_streams is None or peak_viewers is None:
            break

    with open(game_output_dir + '/' + normalized_name + '.json', 'w') as outfile:
        json.dump(game_output, outfile, indent=4, sort_keys=True)

def normalize_name(game_name):
    if game_name in mapping:
        return mapping[game_name]

    normalized_name = game_name
    for char in ":'\"?!%$^*/\\":
        normalized_name = normalized_name.replace(char, '')

    normalized_name = normalized_name.replace('+', 'plus')
    normalized_name = normalized_name.replace('&', 'and')

    # Multiple spaces back to 1, and replaced by _
    normalized_name = ' '.join(normalized_name.split())
    normalized_name = normalized_name.replace(' ', '_')

    normalized_name = unidecode.unidecode(normalized_name)

    return normalized_name

def main(args):
    read_mapping()

    parser = argparse.ArgumentParser(description='GnomeSully Scrapping')
    parser.add_argument("--url", type=str, help="Full game URL to parse")
    parser.add_argument("--game", type=str, help="Game to parse (e.g. Fortnite)")
    parser.add_argument("--streamcamel_games", default=False, action='store_true')
    parser.add_argument("--company", type=str, help="Company's games to parse (e.g. electronic-arts)")
    parser.add_argument("--skip_existing", default=False, action='store_true')

    args = parser.parse_args()
    url = args.url
    game = args.game
    streamcamel_games = args.streamcamel_games
    company = args.company
    skip_existing = args.skip_existing

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
            game_id = None
            if 'game_id' in game:
                game_id = game['game_id']
            scrape_game(game_name, game_id=game_id, skip_existing=skip_existing)

    if company:
        st = StreamCamel()
        games = st.company_games(company)

        logger.info("Obtained {} games".format(len(games)))

        count = 0
        for game in games:
            count += 1
            game_name = game['name']
            game_id = None
            if 'game_id' in game:
                game_id = game['game_id']
            scrape_game(game_name, game_id=game_id, skip_existing=skip_existing)

if __name__ == '__main__':
    logging.basicConfig(level=os.getenv('LOGLEVEL', 'INFO'), stream=sys.stdout, format='%(module)s %(message)s')
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    os.chdir(dname)
    main(sys.argv)
