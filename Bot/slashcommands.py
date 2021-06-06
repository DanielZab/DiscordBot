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
            "name": "name",
            "description": "Url or name of the video",
            "type": 3,
            "required": True
        }
    ]
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


get()
