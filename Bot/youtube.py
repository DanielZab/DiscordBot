import json
import googleapiclient.discovery
import google_auth_oauthlib.flow
import googleapiclient.errors
from googleapiclient.http import MediaIoBaseDownload
import os, io, random
import logging
import asyncio
import json

log = logging.getLogger(__name__)


class YouTube:
    '''
    Performs Youtube searches and loads playlists
    '''
    def __init__(self, key: str) -> None:
        self.key = key

        # Specify YT Data Api: name and version
        self.api_service_name = "youtube"
        self.api_version = "v3"

        # Create youtube client
        self.resource = googleapiclient.discovery.build(self.api_service_name, 
                                                        self.api_version, 
                                                        developerKey=self.key)

    def get_name(self, _id):
        '''
        Get name of youtube video
        '''

        log.info("Getting name of video: " + str(_id))

        # Disable OAuthlib's HTTPS verification when running locally
        # DO NOT leave this option enabled in production
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        # Perform search
        try:
            request = self.resource.videos().list(
                part="snippet",
                id=_id
            )

            response = request.execute()
            
            # Extract title
            title = response['items'][0]['snippet']["title"]

            log.info(f"The title is {title}")

            return title

        except Exception as e:

            log.error("Search failed. Error: " + str(e))

    async def get_search(self, keyword, amount=1, search_type="video") -> list:
        '''
        Perform a Youtube search
        '''

        log.info(f"Performing youtube search. Query: {keyword}, amount: {amount}, type: {search_type}")
        # Disable OAuthlib's HTTPS verification when running locally
        # DO NOT leave this option enabled in production
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        # Set search details
        request = self.resource.search().list(
            part="snippet",
            maxResults=amount,
            type=search_type,
            q=keyword
        )

        url_list = []

        # Perform search
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, request.execute)
            
            # Extract urls
            for i in range(0, amount):
                url_list.append("http://www.youtube.com/watch?v=" + response['items'][i]['id']['videoId'])

            log.info("The search was successful. Results: " + ", ".join(url_list))

        except Exception as e:
            log.error("Search failed. Error: " + str(e))

        finally:
            return url_list

    async def get_playlist_contents(self, _id) -> list:
        '''
        Get contents of a Youtube playlist
        '''

        log.info("Getting contents of playlist. Id: " + str(_id))

        # Disable OAuthlib's HTTPS verification when running locally.
        # DO NOT leave this option enabled in production.
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        # Get contents
        p_token = ''  # Container for the page token. Allows to load playlists that contain more than 50 videos
        result = []
        while True:

            # Set playlist details
            request = self.resource.playlistItems().list(
                part="snippet",
                maxResults=50,
                pageToken=p_token,
                playlistId=_id
            )

            # Get contents
            try:

                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, request.execute)

            except Exception as e:
                log.error("Couldn't get contents. Error: " + str(e))
                break

            # Extract urls
            for item in response['items']:
                video_Id = item['snippet']['resourceId']['videoId']
                result.append('https://www.youtube.com/watch?v=' + video_Id)

            # Check if a next page exists
            try:
                p_token = response['nextPageToken']

            except:
                log.info("Got all contents successfully")
                break

        return result
    
    async def get_captions(self, _id):
        '''
        Get ids of video captions if available
        '''

        log.info("Getting captions")

        # Define method parameters
        request = self.resource.captions().list(
            part="snippet",
            videoId=_id
        )

        # Get captions
        try:

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, request.execute)

        except Exception as e:
            log.error("Couldn't get captions. Error: " + str(e))
            return None

        captions = response["items"]

        # Check if captions exist
        if not len(captions):
            log.info("No captions available")
            return None
        
        log.info("Captions found")

        # Convert json to more convenient form
        captions = list(tuple([e["id"], e["snippet"]["language"]]) for e in captions)

        return captions
    

