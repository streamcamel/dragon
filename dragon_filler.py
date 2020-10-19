#!/usr/bin/python3
# Read buffer streams and upload them. The script runs forever and never gives up

import argparse
import json
import inspect
import uuid
import logging
import time
from datetime import datetime, date, timedelta
import operator
import os
import mysql.connector
import sys
from subprocess import call

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

def validate_env(var):
    value = os.getenv(var)
    if value is None:
        logger.fatal('Missing {} environment variable'.format(var))
        exit(1)

    return value

def sql_make_insert_into(table, keys):
    if len(keys) == 0:
        return ""

    query = "INSERT INTO " + table + " (" + ', '.join(keys) + ") "
    query += "VALUES ("

    first_key = True
    for key in keys:
        if not first_key:
            query += ', '
        query += '%s'
        first_key = False
    query += ") ON DUPLICATE KEY UPDATE "

    first_key = True
    for key in keys:
        if not first_key:
            query += ', '
        query += "{}=VALUES({})".format(key, key)
        first_key = False

    return query

def main(args):
    parser = argparse.ArgumentParser(description='Dragon Filler Service')
    
    database_host = validate_env('SCRATCH_DB_HOST')
    database_name = validate_env('SCRATCH_DB_NAME')
    database_user = validate_env('SCRATCH_DB_USER')
    database_password = validate_env('SCRATCH_DB_PASSWORD') 

    input_path = 'output/games'

    game_records = []

    for filename in os.listdir(input_path):
        logger.info('Reading input file: ' + filename)
        full_path = os.path.join(input_path, filename)

        with open(full_path) as json_file:
            container = json.load(json_file)

            if not 'data' in container:
                logger.warning("json file {} is missing 'data'".format(full_path))
                continue

            if not 'meta-data' in container:
                logger.warning("json file {} is missing 'meta-data'".format(full_path))
                continue

            data = container['data']
            meta_data = container['meta-data']

            if not 'game_id' in meta_data:
                logger.warning("json file {} is missing 'game_id".format(full_path))
                continue 

            game_id = meta_data['game_id']       

            for d in data:
                if 'error' in d:
                    logger.warning("json file {} has error={}".format(full_path, d['error']))
                    continue

                if not 'average_viewers' in d:
                    logger.warning("json file {} is missing 'average_viewers'".format(full_path))
                    continue

                if not 'date' in d:
                    logger.warning("json file {} is missing 'date'".format(full_path))
                    continue

                average_viewers = d['average_viewers']
                average_channels = d['average_channels']
                peak_viewers = d['peak_viewers']

                date = datetime.strptime(d['date'], "%Y-%m")
                game_records.append((game_id, date, average_viewers, peak_viewers, average_channels))

    cnx = mysql.connector.connect(user=database_user, password=database_password,
                                            host=database_host,
                                            database=database_name, use_pure=True)
    cursor = cnx.cursor()

    add_games_sql = sql_make_insert_into('dragon_games_monthly', ['game_id', 'time', 'viewer_count', 'viewer_count_peak', 'stream_count'])
    logger.info('Inserting or Updating ' + str(len(game_records)) + ' records...')
    cursor.executemany(add_games_sql, game_records)
    cnx.commit()
    cnx.close()

if __name__ == '__main__':
    logging.basicConfig(level=os.getenv('LOGLEVEL', 'INFO'), stream=sys.stdout, format='%(module)s %(message)s')
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    os.chdir(dname)
    main(sys.argv)
    
