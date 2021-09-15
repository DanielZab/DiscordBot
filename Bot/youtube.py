import json
from typing import Union
import googleapiclient.discovery
import google_auth_oauthlib.flow
import googleapiclient.errors
from googleapiclient.http import MediaIoBaseDownload
import os, io, random, re
import logging
import asyncio

log = logging.getLogger(__name__)


def get_split_list(li: list, size: int) -> list:
    new_list = []
    start_index = 0
    while len(li[start_index:]) > size:
        new_list.append(li[start_index: start_index + size])
        start_index += size
    new_list.append(li[start_index:])
    return new_list


def convert_duration(duration: str) -> int:
    match = re.match(r"^PT((?P<h>\d{1,2})H)?((?P<m>\d{1,2})M)?((?P<s>\d{1,2})S)?$", duration)
    if match:
        h, m, s = match.group("h") or 0, match.group("m") or 0, match.group("s") or 0
        return round(int(h) * 3600 + int(m) * 60 + int(s))
    log.error(f"Unknown youtube list duration format: {duration}")


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

    async def video_list_query(self, part: str, _id: str):

        # Disable OAuthlib's HTTPS verification when running locally
        # DO NOT leave this option enabled in production
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        request = self.resource.videos().list(
            part=part,
            id=_id
        )

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, request.execute)

    async def get_name(self, _id: str):
        '''
        Get name of youtube video
        '''

        log.info("Getting name of video: " + str(_id))

        # Perform search
        try:
            
            response = await self.video_list_query("snippet", _id)

            assert response

            # Extract title
            title = response['items'][0]['snippet']["title"]

            log.info(f"The title is {title}")

            return title

        except Exception as e:

            log.error("Search failed. Error: " + str(e))

    async def get_search(self, keyword: str, amount: int = 1, search_type: str = "video", full_url: bool = True) -> list:
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
                if full_url:
                    url_list.append("http://www.youtube.com/watch?v=" + response['items'][i]['id']['videoId'])
                else:
                    url_list.append(response['items'][i]['id']['videoId'])

            log.info("The search was successful. Results: " + ", ".join(url_list))

        except Exception as e:
            log.error("Search failed. Error: " + str(e))

        finally:
            return url_list

    async def get_playlist_contents(self, _id, full_url: bool = True) -> list:
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
                if full_url:
                    result.append('https://www.youtube.com/watch?v=' + video_Id)
                else:
                    result.append(video_Id)

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
    
    async def get_length(self, _id: Union[list, str]) -> Union[list, int]:
        
        if isinstance(_id, list):
            split_list = get_split_list(_id, 50)

            lengths_list = [[],[]]

            assert split_list

            for entry in split_list:
                id_string = ",".join(entry)

                response = await self.video_list_query("contentDetails", id_string)

                assert response

                for item in response["items"]:
                    print(item["contentDetails"]["duration"])
                    duration = convert_duration(item["contentDetails"]["duration"])
                    lengths_list[0].append(duration)
                
                difference = 0
                for i in range(len(entry)):
                    item_index = i - difference
                    if entry[i] != response["items"][item_index]["id"]:
                        difference += 1
                        lengths_list[1].append(entry[i])
                        
            return lengths_list

        elif isinstance(_id, str):
            response = await self.video_list_query("contentDetails", _id)
            return convert_duration(response["items"][0]["contentDetails"]["duration"])
    

