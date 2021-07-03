import logging
log = logging.getLogger(__name__)


def create_queue_string(queuelist: list, amount: int) -> list:

    from main import get_name_from_path, convert_time

    # Create containers
    msg_list = []
    new_msg = ""

    log.info("Creating queuelist string")

    for i, entry in enumerate(queuelist):

        # Prepare and convert the database entries
        name = get_name_from_path(entry[0])

        if not name:
            name = str(entry[0])

        length = convert_time(int(entry[1]))
        length = f"{str(length[0]) + ':' if length[0] else ''}{str(length[1]).zfill(2)}:{str(length[2]).zfill(2)}"
        name_string = f"{name if len(name) < 60 else name[:60] + '...'} ({length})"
        name_string = name_string.replace("_", " ").replace("*", " ")

        # Write 'current track' at start of message
        if i == 0:

            new_msg += f"Current track:\n\t\t{name_string}"

        # Create queuelist entry string
        else:

            if i == 1:
                new_msg += "\nQueuelist:"
            
            new_msg += f"\n\t\t{str(i)}. {name_string}"
        
        if amount == i:
            msg_list.append(new_msg)
            break
        
        elif i % 20 == 0 and i != 0:
            msg_list.append(new_msg)
            new_msg = "Continuation:"

    if new_msg != "":
        msg_list.append(new_msg)

    return msg_list

def create_control_board_message_string(name: str, song_timer: int, track_duration: int) -> str:

    from main import convert_time

    log.debug("Creating control board message string")

    cst = convert_time(song_timer)  # Converted song timer
    cctd = convert_time(track_duration)  # Converted current track duration

    new_msg = f"Current track:\n\t**{name if len(name) < 60 else name[:60] + '...'} ({(ccsd[0]+':') if cctd[0] else ''}{str(cctd[1]).zfill(2) + ':' + str(cctd[2]).zfill(2)})**\n "

    length = 18
    for i in range(1, length + 1):
        if i / length <= song_timer / (track_duration - 1):
            new_msg += '█'
        else:
            new_msg += '░'

    if song_timer > track_duration:
        song_timer = track_duration

    return new_msg  # !TEST

    # Add timer to the message
    if cctd[0]:
        new_msg += "\n\t\t\t"
        new_msg += f"{cst[0]}:{str(cst[1]).zfill(2)}:{str(cst[2]).zfill(2)}"
        new_msg += f"/{cctd[0]}:{str(cctd[1]).zfill(2)}:{str(cctd[2]).zfill(2)}"
    else:
        new_msg += "\n\t\t\t\t"
        new_msg += f"{str(cst[1]).zfill(2)}:{str(cst[2]).zfill(2)}"
        new_msg += f"/{str(cctd[1]).zfill(2)}:{str(cctd[2]).zfill(2)}"

    return new_msg
