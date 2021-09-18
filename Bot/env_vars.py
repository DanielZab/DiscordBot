'''
Loads all environment variables from the .env file
'''
import os
from dotenv import load_dotenv


class EnvVariables():
    '''
    Container for all environment variables
    '''
    def __init__(self) -> None:

        load_dotenv()
        # load all environment variables

        # Geniuslyrics api token
        self.GENIUS_TOKEN = os.getenv('GENIUS_ACCESS_TOKEN')

        # Discord bot token
        self.TOKEN = os.getenv('DISCORD_TOKEN')

        # Youtube data api token
        self.DEVELOPER_KEY = os.getenv('YOUTUBE_API_KEY')

        # Whether to hide console automatically
        self.AUTO_HIDE = os.getenv('AUTO_HIDE')

        # MySql database username
        self.SQL_USER = os.getenv('MYSQL_USER')

        # MySql database password
        self.SQL_PW = os.getenv('MYSQL_PW')

        # Id of the role with admin permissions
        self.ADMIN_ROLE_ID = os.getenv('ADMIN_ROLE_ID')
