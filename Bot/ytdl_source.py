'''
Creates youtube-dl sources
'''
import youtube_dl
import discord
import asyncio

# Some youtube-dl settings I found online
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

# Set youtube-dl settings
ytdl_format_options = {
    'format': 'bestaudio/best',
    'quiet': True
}

# Set ffmpeg_options to audio only
ffmpeg_options = {
    'options': '-vn',
}

# Create youtube-dl object
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    '''
    Acts as a audio source, without having to download the song
    Paramters:
        source: The audio source
        data: Extracted video data
        volume: Audio volume
    '''
    def __init__(self, source, *, data, volume=0.1):
        super().__init__(source, volume)

        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False, before_options=False):
        '''
        Creates a YTDLSource instance
        '''

        loop = loop or asyncio.get_event_loop()

        # Extract video data
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        # Assign filename
        filename = data['url'] if stream else ytdl.prepare_filename(data)

        # Set before options
        # These settings prevent the audio stream from ending prematurely
        boptions = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 "

        # Add custom before options to boptions string
        if before_options:
            boptions += before_options

        # Return instance of YTDLSource class with specified settings
        return cls(discord.FFmpegPCMAudio(filename, before_options=boptions, **ffmpeg_options), data=data)
