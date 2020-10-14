#!/usr/bin/python3
# Read current games info and update the database with game info

import argparse
import datetime
from dateutil.relativedelta import *
import errno
import inspect
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
            return int(child.text.replace(",", ""))
    else:
        return -1
    
def main(args):
    parser = argparse.ArgumentParser(description='GnomeSully Scrapping')
    parser.add_argument("--url", type=str, help="Full game URL to parse")
    parser.add_argument("--game", type=str, help="Game to parse (e.g. Fortnite)")

    args = parser.parse_args()
    url = args.url
    game = args.game

    import os
    try:
        os.makedirs('cache')
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    requests_cache.install_cache('cache/cache')
    
    if url is not None:
        content = get_url(url)
        soup = BeautifulSoup(content, features="lxml")
        dom = etree.HTML(str(soup))
        elem = dom.xpath('/html/body/div[2]/div[2]/div[4]/div/div[3]/div/div/div[2]/div')
        for child in elem:
            print(child.text)
    
    if game is not None:
        sdate = datetime.date(2015, 8, 1)
        edate = datetime.date.today()

        d = sdate
        while (d < edate):
            num_viewers = get_game_viewers(game, d)
            print('Game {} got {} viewers for {}'.format(game, num_viewers, d))
            d = d + relativedelta(months = 1)    

if __name__ == '__main__':
    logging.basicConfig(level=os.getenv('LOGLEVEL', 'INFO'), stream=sys.stdout, format='%(module)s %(message)s')
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    os.chdir(dname)
    main(sys.argv)
