from typing import final
from discord import player
import requests
from dotenv import load_dotenv
import os
import json

import logging
log = logging.getLogger(__name__)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Get url
url = "https://discord.com/api/v8/applications/697051009138163732/guilds/456109062833176598/commands"

# Create header
headers = {
    "Authorization": f"Bot {TOKEN}"
}


def get_play_command(choice: list = []):
    p = {
        "name": "play",
        "description": "Plays music. Note: You must be in a channel!",
        "options": [
            {
                "name": "video",
                "description": "Adds a single video to the queue",
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
                "name": "playlist",
                "description": "Adds the contents of a playlist to the queue",
                "type": 2,
                "options": [
                    {
                        "name": "by_url",
                        "description": "Play playlist by its url",
                        "type": 1,
                        "options": [
                            {
                                "name": "url",
                                "description": "The url of the playlist",
                                "type": 3,
                                "required": True
                            },
                            {
                                "name": "index",
                                "description": "At which position in queue",
                                "type": 4
                            },
                            {
                                "name": "limit",
                                "description": "How many songs do you want to add to queue",
                                "type": 4
                            },
                            {
                                "name": "randomize",
                                "description": "Randomize the order of songs",
                                "type": 5
                            }
                        ]
                    }, 
                    {
                        "name": "by_name",
                        "description": "Play playlist by its name",
                        "type": 1,
                        "options": [
                            {
                                "name": "name",
                                "description": "The name of the playlist",
                                "type": 3,
                                "required": True,
                                "choices": choice
                            },
                            {
                                "name": "index",
                                "description": "At which position in queue",
                                "type": 4
                            },
                            {
                                "name": "limit",
                                "description": "How many songs do you want to add to queue",
                                "type": 4
                            },
                            {
                                "name": "randomize",
                                "description": "Randomize the order of songs",
                                "type": 5
                            }
                        ]
                    }
                ]
            }
        ]
    }
    return p


def get_delete_command(choice: list = []):
    delete = {
        "name": "delete",
        "description": "Delete something",
        "options": [
            {
                "name": "playlist",
                "description": "Delete a playlist (Admin only)",
                "type": 1,
                "options": [
                    {
                        "name": "name",
                        "description": "The name of the playlist",
                        "type": 3,
                        "required": True,
                        "choices": choice
                    }
                ]
            }
        ]
    }
    return delete


# region commands
test = {
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

play = get_play_command()

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

queue = {
    "name": "queue",
    "description": "Get the queuelist",
    "options": [
        {
            "name": "amount",
            "description": "How many entries do you want to see",
            "type": 4,
            "required": False
        }
    ]
}

create = {
    "name": "create",
    "description": "Create something",
    "options": [
        {
            "name": "playlist",
            "description": "Create a playlist (Admin only)",
            "type": 1,
            "options": [
                {
                    "name": "url",
                    "description": "The url of the playlist",
                    "type": 3,
                    "required": True
                },
                {
                    "name": "name",
                    "description": "The name of the playlist",
                    "type": 3,
                    "required": True
                }
            ]
        }
    ]
}

_quit = {
    "name": "quit",
    "description": "Close the bot (Admin only)"
}
# endregion


def post(js):
    global url
    global headers

    r = requests.post(url, headers=headers, json=js)
    log.info("Command was sent: " + str(r.content))
    print(r.content)


def get() -> str:
    global url
    global headers
    global json
    r = requests.get(url, headers=headers)
    return r.text


def update_playlist_commands() -> None:

    from file_manager import get_playlists

    # Get all playlists that have an existing directory
    choices = get_playlists()

    # Convert the list elements to the right format
    choices = list(({"name": f"{e}", "value": f"{e}"} for e in choices))

    # Create play and remove commands with new playlist choices
    play = get_play_command(choices)

    delete = get_delete_command(choices)

    # Send commands
    post(play)
    post(delete)

    log.info('Updated play command')


if __name__ == "__main__":
    update_playlist_commands()
# TODO dynamic url
