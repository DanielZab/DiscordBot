'''
Executes all mysql queries to database
There are three kinds of tables:
    queuelist table (contains all necessary details about the queue list)
    playlists table (contains all downloaded playlist names)
    playlist contents table (each table contains all necessary information of a single playlist)
'''
import mysql.connector
import logging

log = logging.getLogger(__name__)


class Database:
    '''
    Connects to database, creates tables and performs queries
    Parameters:
        username:   The username for the connection to the mysql database
        password:   The password for the connection to the mysql database
    '''
    def __init__(self, username, password) -> None:
        self.username = username
        self.password = password

    def execute(self, query) -> list:
        '''
        Starts a connection to database, executes query and returns the result
        '''

        try:

            # Connect to databae
            log.debug("Connecting to database")
            connection = mysql.connector.connect(host='localhost',
                                                 database='discordbot',
                                                 user=self.username,
                                                 password=self.password)

            log.info(f"Executing query: '{query}'")

            # Create cursor
            cursor = connection.cursor()

            # Execute query
            cursor.execute(query)

            # Fetch results
            result = cursor.fetchall()

            # Commit
            connection.commit()

            log.info("Query was successfully executed. Result: " + str(result))

        except Exception as e:

            result = None
            log.error("Connection to db failed. Error: " + str(e))

        finally:

            # Close connection to database
            if connection.is_connected():
                log.debug("Closing connection")
                cursor.close()
                connection.close()

            return result

    def setup(self) -> None:
        '''
        Creates or resets the necessary tables in database
        '''

        # Create queuelist table
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

        # Create playlists table
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

        log.info("Database setup complete")

    def add_to_queue(self, queue_id: int, url: str, path: str, length: float, name: str) -> None:
        '''
        Executes the process of adding a track to the queuelist
        Queue_id specifies the order in which the songs are played
        '''

        # Remove all forbidden chars
        path = path.replace("'", "''")
        name = name.replace("'", "''")

        # Insert into queue
        query = f"INSERT INTO queuelist (queue_id, url, path, length, name) VALUES ({queue_id} ,'{url}', '{path}', {length}, '{name}');"
        self.execute(query)

        log.info(f"{queue_id}/{url}/{path}/{length}/{name} added to queuelist")

    def move_entries(self, index: int) -> None:

        '''
        Increases position in queue list of all entries
        that have a position equal or higher than index by one
        '''

        log.info(f"Moving all entries that are equal or bigger than {index}")

        self.execute(" ".join(["UPDATE queuelist",
                               "SET queue_id = queue_id + 1",
                               f"WHERE queue_id >= {index};"]))

    def insert_into_queue(self, index: int, url: str, length: float, path: str, name: str) -> None:
        '''
        Determines where to add a track into the queue list and
        passes the paramters to the add_to_queue method
        '''

        # Add track at end of queue list if position not specified
        if not index:
            query = "SELECT MAX(queue_id) FROM queuelist;"
            result = self.execute(query)[0][0]
            if result:
                index = 1 + result
            else:
                index = 1

        self.add_to_queue(index, url, path, length, name)

    def get_max_queue_id(self) -> int:
        '''
        Gets and returns index of last track in queue
        '''

        log.debug("Getting maximum queue_id")

        query = "SELECT MAX(queue_id) FROM queuelist;"
        index = self.execute(query)[0][0]

        if not index:
            index = 0

        log.info("Maximum queue_id: " + str(index))
        return index

    def create_playlist_table(self, name: str, url: str) -> None:
        '''
        Creates a table containing the data of all songs of a playlist
        '''

        # Create table
        query = " ".join([f"CREATE TABLE IF NOT EXISTS `{name}` (",
                          "id INT AUTO_INCREMENT,",
                          "url VARCHAR(255) NOT NULL,",
                          "path VARCHAR(255),",
                          "length FLOAT,",
                          "PRIMARY KEY (id)",
                          ")  ENGINE=INNODB;"])
        self.execute(query)

        # Insert playlist name into playlists table
        query = f"INSERT INTO playlists (name, url) VALUES ('{name}', '{url}')"
        self.execute(query)

    def insert_into_playlist(self, name: str, url: str, path: str, length: float) -> None:
        '''
        Inserts a track into its playlist's table
        '''
        # Remove all forbidden chars
        path = path.replace("'", "''")

        # Insert track
        query = f"INSERT INTO `{name}` (url, path, length) VALUES ('{url}', '{path}', {length});"
        self.execute(query)

    def reset_queuelist_ids(self) -> None:
        '''
        Closes gaps in queue list
        '''

        log.info("Closing gaps in queuelist")

        # Get queue list contents
        query = "SELECT id FROM queuelist ORDER BY queue_id"
        queuelist = self.execute(query)

        # Close gaps in queuelist by giving ordered queue_id indieces
        for i, song in enumerate(queuelist, start=1):
            query = f"UPDATE queuelist SET queue_id={i} WHERE id={song[0]}"
        # TODO Test when many songs in queue

    def get_current_url(self, counter) -> str:
        '''
        Gets and returns url of current track
        '''

        log.debug("Getting current url")

        try:
            query = f"SELECT url FROM queuelist WHERE queue_id = {counter}"
            url = self.execute(query)[0][0]

            log.info(f"Current url: {url}")
            return url

        except IndexError:
            log.error("No currrent track")
