import mysql.connector
import logging
import time

from mysql.connector.errors import Error

log = logging.getLogger(__name__)
def execute(query) -> list:
    '''
    Starts a connection to database and executes query
    '''
    # Try connecting to database
    try:
        log.info("Connecting to database")
        connection = mysql.connector.connect(host='localhost',
                                                database='discordbot',
                                                user="root",
                                                password=)

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


print(execute("Select password from test where username = 'Hello'")[0][0])