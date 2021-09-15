from sys import intern
import mysql.connector
import logging
import time, os
from typing import Union

from mysql.connector.errors import Error

log = logging.getLogger(__name__)


class DataBase:
    '''
    Connects to database and performs query
    '''
    def __init__(self, username, password) -> None:
        self.username = username
        self.password = password

    def execute(self, query) -> list:
        '''
        Starts a connection to database and executes query
        '''
        try:
            # Try connecting to database
            log.info("Connecting to database")
            connection = mysql.connector.connect(host='localhost',
                                                 database='discordbot',
                                                 user=self.username,
                                                 password=self.password)

            # Execute and commit query
            log.info(f"Executing query: '{query}'")
            cursor = connection.cursor()
            cursor.execute(query)
            result = cursor.fetchall()
            connection.commit()
            log.info("Query was successfully executed. Result: " + str(result))

        except Exception as e:
            result = None
            log.error("Connection to db failed. Error: " + str(e))

        finally:

            # Close connection to database if still connected
            if connection.is_connected():
                log.info("Closing connection")
                cursor.close()
                connection.close()
            
            return result


    def setup(self) -> None:
        '''
        Creates or resets the necessary tables in database
        '''
        # Create queuelist table if not existent
        query = " ".join(["CREATE TABLE IF NOT EXISTS queuelist (",
                          "id INT AUTO_INCREMENT,",
                          "queue_id INT NOT NULL,",
                          "url VARCHAR(255) NOT NULL,",
                          "path VARCHAR(255),",
                          "length FLOAT,",
                          "name VARCHAR(255),",
                          "PRIMARY KEY (id)",
                          ")  ENGINE=INNODB;"])
        self.execute(query)

        query = " ".join(["CREATE TABLE IF NOT EXISTS playlists (",
                    "id INT AUTO_INCREMENT,",
                    "name VARCHAR(255) NOT NULL,",
                    "url VARCHAR(255) NOT NULL,",
                    "PRIMARY KEY (id)",
                    ")  ENGINE=INNODB;"])
        self.execute(query)

        # Delete all entries from queuelist table
        query = "DELETE FROM queuelist;"
        self.execute(query)

        # Reset primary key
        query = "ALTER TABLE queuelist AUTO_INCREMENT = 1;"
        self.execute(query)

    def add_to_queue(self, queue_id: int, url: str, path: str, length: float, name: str) -> None:
        '''
        Adds a track to the queuelist table
        '''

        path = path.replace("'", "''")
        name = name.replace("'", "''")
        query = f"INSERT INTO queuelist (queue_id, url, path, length, name) VALUES ({queue_id} ,'{url}', '{path}', {length}, '{name}');"
        self.execute(query)

        log.info(f"{queue_id}/{url}/{path}/{length} added to queuelist")

    def move_entries(self, index: int) -> None:

        log.info(f"Moving all entries that are equal or bigger than {index}")

        self.execute(" ".join(["UPDATE queuelist",
                            "SET queue_id = queue_id + 1",
                            f"WHERE queue_id >= {index};"]))

    def insert_into_queue(self, index: int, url: str, length: float, path: str, name: str) -> None:

        log.info(f"Inserting {url} to index {index}")

        if not index:
            query = "SELECT MAX(queue_id) FROM queuelist;"
            result = self.execute(query)[0][0]
            if result:
                index = 1 + result
            else:
                index = 1
        
        self.add_to_queue(index, url, path, length, name)
    
    def get_max_queue_id(self) -> int:
        log.info("Getting maximum queue_id")

        query = "SELECT MAX(queue_id) FROM queuelist;"
        index = self.execute(query)[0][0]

        if not index:
            index = 0

        log.info("Maximum queue_id: " + str(index))
        return index
    
    def create_playlist_table(self, name: str, url: str) -> None:

        query = " ".join([f"CREATE TABLE IF NOT EXISTS `{name}` (",
                    "id INT AUTO_INCREMENT,",
                    "url VARCHAR(255) NOT NULL,",
                    "path VARCHAR(255),",
                    "length FLOAT,",
                    "PRIMARY KEY (id)",
                    ")  ENGINE=INNODB;"])
        self.execute(query)

        query = f"INSERT INTO playlists (name, url) VALUES ('{name}', '{url}')"

        self.execute(query)

    def insert_into_playlist(self, name: str, url: str, path: str, length: float):

        path = path.replace("'", "''")
        query = f"INSERT INTO `{name}` (url, path, length) VALUES ('{url}', '{path}', {length});"
        self.execute(query)
    
    def reset_queuelist_ids(self):
        log.info("Closing gaps in queuelist")
        query = "SELECT id FROM queuelist"
        queuelist = self.execute(query)

        # Close gaps in queuelist by giving ordered queue_id indieces
        for i, song in enumerate(queuelist, start=1):
            query = f"UPDATE queuelist SET queue_id={i} WHERE id={song[0]}"
        # TODO Test when many songs in queue
    
    def get_current_url(self, counter):
        log.info("Getting current url")

        query = f"SELECT url FROM queuelist WHERE queue_id = {counter}"
        try:
            url = self.execute(query)[0][0]
        
            log.info(f"Current url: {url}")
            return url

        except IndexError:
            log.error("No currrent track")
    
