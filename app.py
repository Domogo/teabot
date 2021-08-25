from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from datetime import datetime
import requests, json, logging, time, pytz
from bot_messages import MSG_BOT_HELP, MSG_TEAM_ABSENT


SLACK_BOT_TOKEN="insert bot token here"
SLACK_APP_TOKEN="insert app token here"

LOCUTUS_TEAM="insert team channel here" # channel with all the locutus users
LOCUTUS_BOT_USER="insert bot username here"
LOCUTUS_TROUBLESHOOTING_HOURS = [7, 15]
LOCUTUS_CONFLUENCE="" # a link to info page about team

LOCUTUS_TEAM_MEMBERS = []
IGNORED_THREADS = []
TROUBLESHOOTER = ""

# Initialize a Bolt for Python app
app = App(token=SLACK_BOT_TOKEN)


# @app.message("team members")
def list_team_members(client, message):
    channel = message["channel"]
    thread = message["event_ts"]

    client.chat_postMessage(
        channel=channel,
        text=str(LOCUTUS_TEAM_MEMBERS),
        thread_ts=thread
    )

@app.message(f"<@{LOCUTUS_BOT_USER}> help")
@app.message(f"<@{LOCUTUS_BOT_USER}>\xa0help")
def get_help(client, message):
    channel = message["channel"]
    thread = message.get("thread_ts", message["event_ts"])
    if channel == LOCUTUS_TEAM:
        client.chat_postMessage(
            channel=channel,
            text=MSG_BOT_HELP,
            thread_ts=thread
        )

"""
    Team Locutus members can set themselves on duty, but only in #team_locutus_devs channel
"""
@app.message(f"<@{LOCUTUS_BOT_USER}> start duty")
@app.message(f"<@{LOCUTUS_BOT_USER}>\xa0start duty")
def set_troubleshooter(client, message):
    global TROUBLESHOOTER
    channel = message["channel"]
    thread = message.get("thread_ts", message["event_ts"])
    user = message["user"]

    if thread in IGNORED_THREADS: return

    # channel has to be #locutus_team_devs and the message has to be from locutus team member
    if not channel == LOCUTUS_TEAM and user not in LOCUTUS_TEAM_MEMBERS:
        client.chat_postMessage(
            channel=channel,
            text="""
                *You have no power here!* :nope:\n
            """,
            thread_ts=thread
        )
    else:
        TROUBLESHOOTER = user
        client.chat_postMessage(
            channel=channel,
            text=f"Yerr a troubleshooter, <@{user}>. I hope there's no need to call you.",
            thread_ts=thread
        )


@app.message(f"<@{LOCUTUS_BOT_USER}> get duty")
@app.message(f"<@{LOCUTUS_BOT_USER}>\xa0get duty")
def get_troubleshooter(client, message):
    global IGNORED_THREADS
    channel = message["channel"]
    thread = message.get("thread_ts", message["event_ts"])
    user = message["user"]

    if thread in IGNORED_THREADS: return

    if len(TROUBLESHOOTER) > 0:
        client.chat_postMessage(
            channel=channel,
            text=f"<@{TROUBLESHOOTER}>",
            thread_ts=thread
        )
    else:
        client.chat_postMessage(
            channel=channel,
            text=f"I can't find the troubleshooter! :pepeangry:\nPlease check {LOCUTUS_CONFLUENCE}",
            thread_ts=thread
        )
    # Ignore the thread where the troubleshooter has been called
    IGNORED_THREADS.append(thread)


"""
    Handles any messages not covered by specific events
"""
@app.event("message")
def handle_message_event(client, message):
    channel = message["channel"]
    if channel == LOCUTUS_TEAM: return
    if is_workday() and is_working_hours(): return

    if not message.get("subtype") and not message.get("parent_user_id") and message["user"] not in LOCUTUS_TEAM_MEMBERS and not message["user"] == LOCUTUS_BOT_USER:
        thread = message["event_ts"]

        client.chat_postMessage(
            channel=channel,
            text=MSG_TEAM_ABSENT,
            thread_ts=thread
        )


def is_workday():
    return time.strftime("%u") not in ["6", "7"]


def is_working_hours():
    dt = datetime.now()
    tz = pytz.timezone('Europe/Zagreb')
    dt_croatia = tz.localize(dt)
    return dt_croatia.hour >= LOCUTUS_TROUBLESHOOTING_HOURS[0] and dt_croatia.hour < LOCUTUS_TROUBLESHOOTING_HOURS[1]


"""
    on app start, get #locutus_team_devs members
"""
def get_locutus_team_members(client):
    global LOCUTUS_TEAM_MEMBERS

    response = client.conversations_members(
        token=SLACK_BOT_TOKEN,
        channel=LOCUTUS_TEAM
    )
    LOCUTUS_TEAM_MEMBERS = list(filter(lambda member: member != LOCUTUS_BOT_USER, response["members"]))



if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
    get_locutus_team_members(app.client)
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
