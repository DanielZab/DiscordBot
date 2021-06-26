from discord import player
import requests
from dotenv import load_dotenv
import os


url = "https://discord.com/api/v8/applications/697051009138163732/guilds/456109062833176598/commands"

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

json = {
    "name": "test",
    "description": "Send a random adorable animal photo",
    "options": [
        {
            "name": "animal",
            "description": "The type of animal",
            "type": 3,
            "required": True,
            "choices": [
                {
                    "name": "Dog",
                    "value": "animal_dog"
                },
                {
                    "name": "Cat",
                    "value": "animal_cat"
                },
                {
                    "name": "Penguin",
                    "value": "animal_penguin"
                }
            ]
        },
        {
            "name": "only_smol",
            "description": "Whether to show only baby animals",
            "type": 5,
            "required": False
        }
    ]
}

play = {
    "name": "play",
    "description": "Plays music. Note: You must be in a channel!",
    "options": [
        {
            "name": "video",
            "description": "Url or name of the video",
            "type": 2,
            "options": [
                {
                    "name": "by_name",
                    "description": "Searches for a video in Youtube by its name",
                    "type": 1,
                    "options": [
                        {
                            "name": "name",
                            "description": "The name of the video",
                            "type": 3,
                            "required": True
                        },
                        {
                            "name": "amount",
                            "description": "The number of results. Default value is 1",
                            "type": 4
                        },
                        {
                            "name": "index",
                            "description": "At which position in queue",
                            "type": 4
                        }
                    ]
                },
                {
                    "name": "by_url",
                    "description": "Searches for a video in Youtube by its url",
                    "type": 1,
                    "options": [
                        {
                            "name": "url",
                            "description": "The url of the video",
                            "type": 3,
                            "required": True
                        },
                        {
                            "name": "index",
                            "description": "At which position in queue",
                            "type": 4
                        }
                    ]
                }
            ]
        },
        {
            "name": "postion",
            "description": "The position in the queuelist.",
            "type": 4
        }
    ]
}

control = {
    "name": "control",
    "description": "Show the control panel"
}

skip = {
    "name": "skip",
    "description": "Skip a song",
    "options": [
        {
            "name": "amount",
            "description": "Amount of songs to be skipped",
            "type": 4,
            "required": False
        }
    ]
}

back = {
    "name": "back",
    "description": "Play a previous song",
    "options": [
        {
            "name": "amount",
            "description": "How many songs",
            "type": 4,
            "required": False
        }
    ]
}

fast_forward = {
    "name": "fast_forward",
    "description": "Fast forward a song",
    "options": [
        {
            "name": "amount",
            "description": "How many seconds",
            "type": 4,
            "required": False
        }
    ]
}

rewind = {
    "name": "rewind",
    "description": "Rewind a song",
    "options": [
        {
            "name": "amount",
            "description": "How many seconds",
            "type": 4,
            "required": False
        }
    ]
}

pause = {
    "name": "pause",
    "description": "Pause or resume a song"
}

stop = {
    "name": "stop",
    "description": "Stop the player and remove all songs"
}

# For authorization, you can use either your bot token
headers = {
    "Authorization": f"Bot {TOKEN}"
}


def post(js):
    global url
    global headers

    r = requests.post(url, headers=headers, json=js)
    print(r.content)


def get():
    global url
    global headers
    global json
    r = requests.get(url, headers=headers)
    print(r.text)


post(stop)
post(pause)
post(rewind)
post(fast_forward)
post(back)
input(get())
