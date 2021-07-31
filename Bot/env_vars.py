# Environment variables loader
import os
from dotenv import load_dotenv


class EnvVariables():
    '''
    Container for all environment variables
    '''
    def __init__(self) -> None:

        load_dotenv()
        # load all environment variables
        self.GENIUS_TOKEN = os.getenv('GENIUS_ACCESS_TOKEN')
        self.TOKEN = os.getenv('DISCORD_TOKEN')
        self.DEVELOPER_KEY = os.getenv('YOUTUBE_API_KEY')
        self.AUTO_HIDE = os.getenv('AUTO_HIDE')
        self.SQL_USER = os.getenv('MYSQL_USER')
        self.SQL_PW = os.getenv('MYSQL_PW')
        self.ADMIN_ROLE_ID = os.getenv('ADMIN_ROLE_ID')