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

def main(args):
    parser = argparse.ArgumentParser(description='Dragon Filler Service')
    
    database_host = validate_env('SCRATCH_DB_HOST')
    database_name = validate_env('SCRATCH_DB_NAME')
    database_user = validate_env('SCRATCH_DB_USER')
    database_password = validate_env('SCRATCH_DB_PASSWORD') 

    # for filename in os.listdir(input_path):
    #     # Make sure file has no _pending
    #     if filename.find('_pending') != -1:
    #         continue

    #     if not filename.endswith('.zip'):
    #         continue

    #     logger.info('Reading input file: ' + filename)
    #     container = utils.loadContainer(os.path.join(input_path, filename))

    #     if not ('data' in container and 'meta-data' in container):
    #         logger.warning('Invalid JSON in ' + filename)
    #         continue

    #     data = container['data']
    #     if 'meta-data' in container:
    #         start_time = container['meta-data']['start-time']

    #     if start_time is None:
    #         logger.warning('No start-time in ' + filename)
    #         continue

    #     logger.info('Timestamp: ' + start_time)

    #     stream_records = []
    #     stream_info = []
    #     try:
    #         for stream in data:
    #             if ('id' in stream and 'game_id' in stream and 'viewer_count' in stream):
    #                 stream_records.append(
    #                     (
    #                     start_time,
    #                     stream['id'], 
    #                     stream['game_id'],
    #                     stream['viewer_count']
    #                     ))

    #                 stream_info.append(
    #                     (
    #                     stream['id'], 
    #                     stream['user_id'], 
    #                     stream['game_id'],
    #                     stream['type'],
    #                     stream['language'],
    #                     0 # Twitch Source is 0
    #                     ))
                    
    #         try:
    #             if not database_name is None:
    #                 cnx = mysql.connector.connect(user=database_user, password=database_password,
    #                                         host=database_host,
    #                                         database=database_name, use_pure=True)
    #                 cursor = cnx.cursor()

    #                 add_stream_sql = utils.sql_make_insert_into(settings.streams_table_name, ['time', 'id', 'game_id', 'viewer_count'])
    #                 add_stream_info_sql = utils.sql_make_insert_into(settings.streams_info_table_name, ['id', 'user_id', 'game_id', 'type', 'language', 'source'])

    #                 logger.info('Inserting or Updating ' + str(len(stream_records)) + ' records...')
    #                 utc_pre_db_time = datetime.utcnow()
    #                 cursor.executemany(add_stream_sql, stream_records)
    #                 cursor.executemany(add_stream_info_sql, stream_info)
    #                 utc_postdb_time = datetime.utcnow()
    #                 logger.info('Done in ' + str(utc_postdb_time - utc_pre_db_time) + ' seconds. Cleaning up connection')
    #             else:
    #                 logger.info('Null DB Would insert ' + str(len(stream_records)) + ' records.')
    #         except mysql.cursor.Error as err:
    #             logger.critical("Can't insert stream data: {}".format(err))
            
    #         if not database_name is None:
    #             cnx.commit()
    #             cursor.close()
    #             cnx.close()

    #             logger.info('Updating rollup')

    #             # 2020-06-09 13:55 format (in UTC)

    #             now_utc = datetime.strptime(start_time + ' -0000', '%Y-%m-%d %H:%M %z')

    #             # TODO: Change begin_utc to at least week ago
    #             # since we want to catch up any company changes that may have been missed


    #             # Need to floor to the 10 minutes
    #             # If 13 minutes --> 10 minutes
    #             # If 10 minutes --> 10 minutes
    #             # If 27 minutes --> 20 minutes

    #             # Figure out how many minutes we have
    #             # Then round down
    #             minutes = (now_utc.minute // 10) * 10

    #             begin_utc = now_utc.replace(microsecond=0, minute=minutes, second=0)
    #             end_utc = begin_utc + timedelta(minutes=10)

    #             logger.info('begin_utc {} to end_utc {}'.format(begin_utc.strftime("%Y-%m-%d %H:%M"), end_utc.strftime("%Y-%m-%d %H:%M")))

    #             script_rollup_path = os.path.join(get_script_dir(), 'rollup.py')
    #             call([sys.executable, script_rollup_path, '--date_begin=' + begin_utc.strftime("%Y-%m-%d %H:%M"), '--date_end=' + end_utc.strftime("%Y-%m-%d %H:%M")])

    #             os.remove(os.path.join(input_path, filename))
    #             logger.info('Deleted input file: ' + os.path.join(input_path, filename))

    #     except mysql.connector.Error as err:
    #         logger.critical("Cannot connect to database {}".format(err))

if __name__ == '__main__':
    logging.basicConfig(level=os.getenv('LOGLEVEL', 'INFO'), stream=sys.stdout, format='%(module)s %(message)s')
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    os.chdir(dname)
    main(sys.argv)
    
