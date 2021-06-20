import googleapiclient.discovery
import os
import logging

log = logging.getLogger(__name__)


class YouTube:
    '''
    Performs Youtube searches and loads playlists
    '''
    def __init__(self, key) -> None:
        self.key = key

        # Specify YT Data Api: name and version
        self.api_service_name = "youtube"
        self.api_version = "v3"

        # Create youtube client
        self.resource = googleapiclient.discovery.build(self.api_service_name, 
                                                        self.api_version, 
                                                        developerKey=self.key)

    def get_search(self, keyword, amount=1, search_type="video") -> list:
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
            response = request.execute()
            
            # Extract urls
            for i in range(0, amount):
                url_list.append("http://www.youtube.com/watch?v=" + response['items'][i]['id']['videoId'])

            log.info("The search was successful. Results: " + ", ".join(url_list))

        except Exception as e:
            log.error("Search failed. Error: " + str(e))

        finally:
            return url_list

    def get_playlist_contents(self, url) -> list:
        '''
        Get contents of a Youtube playlist
        '''

        log.info("Getting contents of playlist. Url: " + str(url))

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
                playlistId=url
            )

            # Get contents
            try:
                response = request.execute()
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
    
    def get_name(self, _id):
        '''
        
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
