import discord
import asyncio
import logging
import string_creator
log = logging.getLogger(__name__)


class MyClient(discord.Client):
    '''
    Extends the discord.Client class in order to add some custom properties
    '''

    def __init__(self) -> None:

        super().__init__()
        self.setup()
    
    def setup(self) -> None:
        
        # Create containers for current voice channel and its name
        self.channel = None
        self.vc = None

        # Create counter for current track
        self.queue_counter = 1

        # Indicates if all requested songs have been played
        self.waiting = True

        # Lock which guarantees exclusive access to a shared resource
        self.lock = asyncio.Lock()

        # To download in between of songs
        self.placeholders = []  # FIXME

        # A list of emojis representing numbers
        self.emoji_list = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🚫']

        # Container for all emojis
        self.custom_emojis = dict()

        # Indicates how long a song has been played
        self.song_timer = 0 

        # Before options for the player, can specify different things such as where to start
        # or playback speed
        self.boption = None

        # Containter for all messages containing control boards
        self.control_board_messages = []

        # Container for all messages containing the queuelist
        self.queuelist_messages = []

        # The name and duration of the current track
        self.current_track_name = None
        self.current_track_duration = 0
        self.current_thumbnail = None

        # Container for the id of the admin role
        self.admin_role_id = None

        # Indicates whether player is paused manually
        self.force_stop = False

        # Indicates whether to repeat current song
        self.repeat = False

        # How often to repeat
        self.repeat_counter = -1  

    def vc_check(self) -> bool:
        '''
        Checks whether player is paused/playing a song
        '''
        return self.vc and (self.vc.is_paused() or self.vc.is_playing())
    
    def play_with_boption(self, boption) -> None:
        '''
        Resets the current track with the boption settings
        '''

        if self.vc_check():
        
            self.queue_counter -= 1
            self.boption = boption
            self.vc.stop()
            return True
        
        else:
            return False

    def start_player(self):

        self.force_stop = False

        import main.check_player
        main.check_player.start()
    
    def stop(self, force: bool = False):

        if force:
            log.info("Forcing music stop")
            self.force_stop = True

        if self.vc_check():
            log.info("Stopping music")
            self.vc.stop()

    def reset_current_song_data(self) -> None:

        self.current_track_name = None
        self.current_track_duration = 0
        self.current_thumbnail = None
    
    def set_db(self, db) -> None:
        self.db = db

    async def update_queuelist_messages(self) -> None:

        log.info("Updating queuelists")

        query = f"SELECT path, length FROM queuelist WHERE queue_id >= {self.queue_counter} ORDER BY queue_id"
        queuelist = self.db.execute(query)

        # Delete all messages if there are no more songs
        if len(queuelist) < 1:

            log.info("No more songs, deleting all queuelist messages")
            for messages in self.queuelist_messages:

                for message in messages[0]:

                    await message.delete()

            return

        for messages, amount in self.queuelist_messages:

            new_messages = string_creator.create_queue_string(queuelist, amount)

            for i, message in enumerate(messages):

                try:

                    await message.edit(content=new_messages[i])

                except IndexError:

                    await message.delete()
                
                except discord.errors.NotFound:

                    log.warning("Could not update queuelist message, it was not found")
    
    async def delete_queuelist_messages(self):

        log.info("Deleting all queuelist messages")

        for message_tuple in self.queuelist_messages:
            for msg in message_tuple[0]:
                try:
                    await msg.delete()
                except Exception as e:
                    log.error("Couldn't delete control board message. Error: " + str(e))
    
    async def delete_control_board_messages(self):

        for message in self.control_board_messages:
            await message.delete()
