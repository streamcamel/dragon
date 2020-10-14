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

    content = response.content
    return content

def get_game_viewers(game, date):
    base_url = 'https://sullygnome.com/game/' + game + '/'
    date_string = date.strftime("%Y%B").lower()
    url = base_url + date_string

    content = get_url(url)

    soup = BeautifulSoup(content, features="lxml")
    dom = etree.HTML(str(soup))
    elem = dom.xpath('/html/body/div[2]/div[2]/div[4]/div/div[3]/div/div/div[2]/div')
    if elem is not None:
        for child in elem:
            value = child.text.replace(",", "")
            if is_int(value):
                return int(value)
            else:
                logging.warning("Game {} for date {} doesn't have a parsable viewers count: {}", game, date, child.text)
                return -1
    else:
        return -1
    
def main(args):
    parser = argparse.ArgumentParser(description='GnomeSully Scrapping')
    parser.add_argument("--url", type=str, help="Full game URL to parse")
    parser.add_argument("--game", type=str, help="Game to parse (e.g. Fortnite)")

    args = parser.parse_args()
    url = args.url
    game = args.game

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
            game_output.append(game_entry)
            d = d + relativedelta(months = 1)

        with open(game_output_dir + '/' + game + '.json', 'w') as outfile:
            json.dump(game_output, outfile, indent=4, sort_keys=True)

if __name__ == '__main__':
    logging.basicConfig(level=os.getenv('LOGLEVEL', 'INFO'), stream=sys.stdout, format='%(module)s %(message)s')
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    os.chdir(dname)
    main(sys.argv)
