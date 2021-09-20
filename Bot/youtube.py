'''
Connects to the youtube data api
'''
from typing import Union, Tuple
import googleapiclient.discovery
import googleapiclient.errors
import os, re
import logging
import asyncio

log = logging.getLogger(__name__)

# Disable OAuthlib's HTTPS verification when running locally
# DO NOT leave this option enabled in production
# os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"


def get_split_list(li: list, size: int) -> list:
    '''
    Splits a list into multiple lists of fixed size
    '''

    new_list = []
    start_index = 0
    while len(li[start_index:]) > size:
        new_list.append(li[start_index: start_index + size])
        start_index += size
    new_list.append(li[start_index:])
    return new_list


def convert_duration(duration: str) -> int:
    '''
    Converts the youtube time format to seconds
    '''

    # Match string
    match = re.match(r"^PT((?P<h>\d{1,2})H)?((?P<m>\d{1,2})M)?((?P<s>\d{1,2})S)?$", duration)

    # Check if matched
    if match:

        # Extract hours, seconds and minutes
        h, m, s = match.group("h") or 0, match.group("m") or 0, match.group("s") or 0

        # Convert to seconds
        return round(int(h) * 3600 + int(m) * 60 + int(s))

    log.error(f"Unknown youtube list duration format: {duration}")


class YouTube:
    '''
    Connects to the youtube data api and executes search queries
    Paramters:
        key: The youtube data api developer key/token
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

    async def video_list_query(self, part: str, _id: str) -> dict:
        '''
        Gets the details of a video by its id
        '''

        # Define settings
        request = self.resource.videos().list(
            part=part,
            id=_id
        )

        # Run search in asnyc executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, request.execute)

    async def get_name(self, _id: str) -> str:
        '''
        Gets name of youtube video by its id
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
        Performs a youtube search
        Parameters:
            keyword:    The youtube search query
            amount:     The amount of result to return
            search_type:Whether to search for a video, playlist or channel
            full_url:   Indicates whether to return the full url or only the ids
        Returns a list containing the urls/ids
        '''

        log.info(f"Performing youtube search. Query: {keyword}, amount: {amount}, type: {search_type}")

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
            
            # Run search query in async executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, request.execute)
            
            # Extract ids/urls
            for i in range(0, amount):

                # Check whether to append whole url or id only
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

        # Create page token container. For playlists with more than 50 videos
        # each 50 videos a new page needs to be loaded
        p_token = ''

        # Get playlist contents
        result = []
        while True:

            # Set playlist search details
            request = self.resource.playlistItems().list(
                part="snippet",
                maxResults=50,
                pageToken=p_token,
                playlistId=_id
            )

            try:

                # Execute search query in asnyc executor
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, request.execute)

            except Exception as e:
                log.error("Couldn't get contents. Error: " + str(e))
                break

            # Extract urls
            for item in response['items']:
                video_Id = item['snippet']['resourceId']['videoId']

                # Check whether to return full url or only the ids
                if full_url:
                    result.append('https://www.youtube.com/watch?v=' + video_Id)
                else:
                    result.append(video_Id)

            # Try to get next token, will fail if there's no next page
            try:
                p_token = response['nextPageToken']

            except KeyError:
                log.info("Got all contents successfully")
                break

        return result
    
    async def get_captions(self, _id) -> Tuple[str, str]:
        '''
        Gets the ids of youtube video captions if available
        Returns a tuple containing the id of the captions and their language
        '''

        log.info("Getting captions")

        # Define search query settings
        request = self.resource.captions().list(
            part="snippet",
            videoId=_id
        )

        try:

            # Execute query in async executor
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, request.execute)

        except Exception as e:
            log.error("Couldn't get captions. Error: " + str(e))
            return

        # Extract captions
        captions = response["items"]

        # Check if captions exist
        if not len(captions):
            log.info("No captions available")
            return
        
        log.info("Captions found")

        # Convert json to more convenient form
        captions = list(tuple([e["id"], e["snippet"]["language"]]) for e in captions)

        return captions
    
    async def get_length(self, _id: Union[list, str]) -> Union[list, int]:
        '''
        Gets the length of a single youtube video or a video list
        Returns the video length in seconds/a list with all successfully
        retrieved video lengths, and their ids
        '''

        # Check if passed parameter is a list
        if isinstance(_id, list):

            # Split list into smaller lists
            split_list = get_split_list(_id, 50)

            # Create results container
            lengths_list = [[], []]

            assert split_list

            for entry in split_list:

                # Perform search query
                id_string = ",".join(entry)
                response = await self.video_list_query("contentDetails", id_string)

                assert response

                # Extract durations
                for item in response["items"]:
                    duration = convert_duration(item["contentDetails"]["duration"])
                    lengths_list[0].append(duration)
                
                # Add all ids whose lengths were retrieved to results list
                # This process eliminates all ids that were invalid
                difference = 0
                for i in range(len(entry)):
                    item_index = i - difference
                    if entry[i] != response["items"][item_index]["id"]:
                        difference += 1
                        lengths_list[1].append(entry[i])
                        
            return lengths_list

        # Check if passed parameter is a string
        elif isinstance(_id, str):

            # Perform search query
            response = await self.video_list_query("contentDetails", _id)

            # Extract, convert and return duration
            return convert_duration(response["items"][0]["contentDetails"]["duration"])
        
        # Error detection
        log.error("Unknown paramter in get_length " + str(_id))
