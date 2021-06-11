import mysql.connector
import logging
import time

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
                         "queue_id INT NOT NULL,"
                         "url VARCHAR(255) NOT NULL,",
                         "path VARCHAR(255),",
                         "length FLOAT,",
                         "last_played DATETIME,",
                         "PRIMARY KEY (id)",
                         ")  ENGINE=INNODB;"])
        self.execute(query)

        # Delete all entries from queuelist table
        query = "DELETE FROM queuelist;"
        self.execute(query)

        # Reset primary key
        query = "ALTER TABLE queuelist AUTO_INCREMENT = 1;"
        self.execute(query)

    def add_to_queue(self, queue_id, url, path, length) -> None:

        #TODO: Implement
        query = f"INSERT INTO queuelist (queue_id, url, path, length) VALUES ({queue_id} ,'{url}', '{path}', {length});"
        self.execute(query)
        log.info(f"{queue_id}/{url}/{path}/{length} added to queue list")