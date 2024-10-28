import os
import asyncio
import discord
import shutil
import re
import json

import random
from dotenv import load_dotenv
from discord.ext import commands, tasks
from utils.ai import generate_response
from utils.split_response import split_response
from colorama import init, Fore, Style
from datetime import datetime

load_dotenv(dotenv_path="config/.env")
init()
# INTENTS=discord.Intents.default()
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX")
OWNER_ID = int(os.getenv("OWNER_ID", 0))
TRIGGER = os.getenv("TRIGGER", "").lower().split(",")

bot = commands.Bot(command_prefix=PREFIX, help_command=None)
bot.owner_id = OWNER_ID
bot.allow_dm = True
bot.allow_gc = True
bot.active_channels = set()
bot.ignore_users = []
bot.message_history = {}
bot.paused = False
bot.realistic_typing = os.getenv("REALISTIC_TYPING").lower()
bot.anti_age_ban = os.getenv("ANTI_AGE_BAN").lower()

MAX_HISTORY = 30


def append_to_json(input_string, json_file="config/presetMessage.json"):
    # Extract strings inside square brackets using regex
    matches = re.findall(r'\[(.*?)\]', input_string)
    print(input_string)
    if matches:
        # Split the extracted string by commas and strip any extra spaces
        new_data = [item.strip() for item in matches[0].split(',')]
        
        try:
            # Read the existing JSON data
            with open(json_file, 'r') as file:
                data = json.load(file)
            
            # Ensure the existing data is a list
            if not isinstance(data, list):
                data = []
        except (FileNotFoundError, json.JSONDecodeError):
            # If the file does not exist or is not valid JSON, start with an empty list
            data = []
        
        # Append the new data to the existing list
        data.extend(new_data)
        
        # Save the updated list back to the JSON file
        with open(json_file, 'w') as file:
            json.dump(data, file, indent=4)
        
        print(f"Data successfully added to {json_file}")
    else:
        print("No valid strings found in the input.")


def get_random_string(json_file="config/presetMessage.json"):
    try:
        # Read the existing JSON data
        with open("config/presetMessage.json", 'r') as file:
            data = json.load(file)
        
        # Ensure the data is a list and not empty
        if isinstance(data, list) and len(data)>0:
            # Return a random string from the list
            return random.choice(data)
        else:
            print("The JSON file does not contain a valid list or is empty.")
            return None
    except (FileNotFoundError, json.JSONDecodeError):
        print("The JSON file does not exist or is not valid.")
        return None
def clear_json_file(file_path="config/presetMessage.json"):
    """
    Clears the contents of the specified JSON file by resetting it to an empty list.
    
    :param file_path: The path to the JSON file.
    """
    try:
        # Reset the data to an empty list or dictionary
        empty_data = {}

        # Write the empty data back to the file
        with open(file_path, 'w') as file:
            json.dump(empty_data, file)

        print("JSON file has been cleared successfully.")

    except Exception as e:
        print(f"An error occurred while clearing the JSON file: {e}")


def transform_user_messages(data):
    """
    Transforms user messages into the desired format.
    
    Args:
        data (dict): Original data where the keys are user IDs, 
                     and the values are lists of messages.
    
    Returns:
        list: A list of dictionaries with "role" and "content".
    """
    transformed = []
    
    for user_id, messages in data.items():
        # Combine the messages into a single string separated by commas
        content = ", ".join(messages)
        
        # Create the transformed object
        transformed.append({"role": "user", "content": content})
    
    return transformed


async def fetch_recent_chats(channel_id):
    """Fetches the last messages from the last three users who texted, excluding mentions of the bot."""
    channel = bot.get_channel(channel_id)  # Fetch the channel object using the channel ID
    if channel is None:
        print(f"Channel with ID {channel_id} not found.")
        return

    user_messages = {}
    
    # Fetch the last 100 messages from the channel
    async for message in channel.history(limit=100):
        # Check if the message mentions the bot
        if bot.user in message.mentions:
            continue
        if message.content.startswith("~"):
            continue
        
        # If the author is not a bot and is not already tracked
        if not message.author.bot and message.author != bot.user:
            author_id = str(message.author.id)
            if author_id not in user_messages:
                user_messages[author_id] = []
            
            user_messages[author_id].append(message.content)

            # Limit to last 5 messages
            if len(user_messages[author_id]) > 5:
                user_messages[author_id] = user_messages[author_id][-5:]

    # Get the last 3 users who messaged (based on their appearance in the message history)
    recent_users = list(user_messages.keys())[-3:]

    print(user_messages)
    instruction="Act as a normal user on Discord and type in only lowercase,"
    re=await generate_response(prompt=user_messages[author_id][0],instructions=instruction,history=transform_user_messages(user_messages))
    print(re)
    return f"<@{list(user_messages.keys())[0]}> {re}"

def check_periodic_reply():
    with open("config/toogleReply.txt", "r") as file:
        for line in file:
            # Check if the line contains the PERIODIC_REPLY setting
            if "PERIODIC_REPLY" in line:
                # Split the line into the variable name and value
                key, value = line.strip().split("=")
                # Check if the value is 'true'
                if key == "PERIODIC_REPLY" and value.lower() == "true":
                    return True
                else:
                    return False
    return False

# Usage
if check_periodic_reply():
    print("Periodic reply is enabled.")
else:
    print("Periodic reply is disabled.") 
# Function to send a message every 20 minutes
async def periodic_message_task():
    
    while True:
        message_content = get_random_string()
        for channel_id in bot.active_channels:
            channel = bot.get_channel(channel_id)
            if channel:
                try:
                    if message_content != None:
                        await channel.send(message_content)
                except Exception as e:
                    print(f"Failed to send periodic message: {e}")
        await asyncio.sleep(1200)  # 20 minutes in seconds

# Function to reply based on history every 5 minutes
async def reply_based_on_history_task():
     while True:
        if  check_periodic_reply()== False:
            continue
        message_content = get_random_string()
        for channel_id in bot.active_channels:
            channel = bot.get_channel(channel_id)
            if channel:
                try:
                  res=await fetch_recent_chats(channel_id)
                  await channel.send(res)
                except Exception as e:
                    print(f"Failed to send periodic message: {e}")
        await asyncio.sleep(1500)  # 20 minutes in seconds
    # 5 minutes in seconds
def clear_console():
    os.system("cls" if os.name == "nt" else "clear")


def get_terminal_size():
    columns, _ = shutil.get_terminal_size()
    return columns


def create_border(char="═"):
    width = get_terminal_size()
    return char * (width - 2)  # -2 for the corner characters


def print_header():
    width = get_terminal_size()
    border = create_border()
    title = "AI Selfbot by Najmul"
    padding = " " * ((width - len(title) - 2) // 2)

    print(f"{Fore.CYAN}╔{border}╗")
    print(f"║{padding}{Style.BRIGHT}{title}{Style.NORMAL}{padding}║")
    print(f"╚{border}╝{Style.RESET_ALL}")


def print_separator():
    print(f"{Fore.CYAN}{create_border('─')}{Style.RESET_ALL}")


@bot.event
async def on_ready():
    bot.selfbot_id = bot.user.id  # this has to be here, or else it won't work
    asyncio.create_task(periodic_message_task())
    asyncio.create_task(reply_based_on_history_task())
    clear_console()

    print_header()
    print(
        f"AI Selfbot successfully logged in as {Fore.CYAN}{bot.user.name} ({bot.selfbot_id}){Style.RESET_ALL}.\n"
    )

    print("Active in the following channels:")

    for channel_id in bot.active_channels:
        channel = bot.get_channel(channel_id)
        if channel:
            try:
                print(f"- #{channel.name} in {channel.guild.name}")
            except Exception:
                pass

    print(
        f"\n{Fore.LIGHTBLACK_EX}Join the Discord server for support and news on updates: https://discord.gg/yUWmzQBV4P{Style.RESET_ALL}"
    )

    print_separator()


if os.path.exists("config/instructions.txt"):
    with open("config/instructions.txt", "r", encoding="utf-8") as file:
        instructions = file.read()
else:
    print(
        "Instructions file not found. Please provide instructions in config/instructions.txt"
    )
    exit(1)
 
if os.path.exists("config/channels.txt"):
    with open("config/channels.txt", "r") as f:
        for line in f:
            channel_id = int(line.strip())
            bot.active_channels.add(channel_id)
else:
    print("Active channels file not found. Creating a new one.")
    with open("config/channels.txt", "w"):
        pass

if os.path.exists("config/ignoredusers.txt"):
    with open("config/ignoredusers.txt", "r") as f:
        for line in f:
            user_id = int(line.strip())
            bot.ignore_users.append(user_id)
else:
    print("Ignored users file not found. Creating a new one.")
    with open("config/ignoredusers.txt", "w"):
        pass


def should_ignore_message(message):
    return (
        message.author.id in bot.ignore_users
        or message.author.id == bot.selfbot_id
        or message.author.bot
    )


def is_trigger_message(message):
    mentioned = (
        bot.user.mentioned_in(message)
        and "@everyone" not in message.content
        and "@here" not in message.content
    )
    replied_to = (
        message.reference
        and message.reference.resolved
        and message.reference.resolved.author.id == bot.selfbot_id
    )
    is_dm = isinstance(message.channel, discord.DMChannel) and bot.allow_dm
    is_group_dm = isinstance(message.channel, discord.GroupChannel) and bot.allow_gc

    content_has_trigger = any(
        re.search(rf"\b{re.escape(keyword)}\b", message.content.lower())
        for keyword in TRIGGER
    )

    return (
        content_has_trigger
        or mentioned
        or (replied_to and mentioned)
        or is_dm
        or is_group_dm
        and (mentioned or replied_to or content_has_trigger)
    )


def update_message_history(author_id, message_content):
    print("update history")
    if author_id not in bot.message_history:
        bot.message_history[author_id] = []
    bot.message_history[author_id].append(message_content)
    bot.message_history[author_id] = bot.message_history[author_id][-MAX_HISTORY:]


async def generate_response_and_reply(message, prompt, history):
    response = await generate_response(prompt, instructions, history)
    chunks = split_response(response)

    if len(chunks) > 3:
        chunks = chunks[:3]
        print(f"{datetime.now().strftime('[%H:%M:%S]')} Response too long, truncating.")

    for chunk in chunks:
        chunk = chunk.replace(
            "@", "@\u200b"
        )  # Prevent mentions by replacing them with a hidden whitespace

        if bot.anti_age_ban == "true":
            chunk = re.sub(
                r"(?<!\d)([0-9]|1[0-2])(?!\d)|\b(zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b",
                "\u200b",
                chunk,
                flags=re.IGNORECASE,
            )

        print(
            f'{datetime.now().strftime("[%H:%M:%S]")} {message.author.name}: {prompt}'
        )
        print(
            f'{datetime.now().strftime("[%H:%M:%S]")} Responding to {message.author.name}: {chunk}'
        )
        print_separator()

        try:
            async with message.channel.typing():
                if bot.realistic_typing == "true":
                    await asyncio.sleep(int(len(chunk) / 15))

                await message.reply(chunk)
        except Exception as e:
            print(f"Error sending message: {e}")

        await asyncio.sleep(1.5)

    return response
def toggle_periodic_reply(file_path):
    """
    Toggles the PERIODIC_REPLY value between true and false in the specified .txt file.
    
    :param file_path: The path to the .txt file.
    """
    try:
        # Read the content of the file
        with open(file_path, 'r') as file:
            lines = file.readlines()

        # Variable to check if the keyword was found
        keyword_found = False

        # Iterate through the lines to find and toggle the PERIODIC_REPLY value
        for i, line in enumerate(lines):
            if "PERIODIC_REPLY=" in line:
                current_value = line.strip().split("=")[1].lower()
                new_value = "false" if current_value == "true" else "true"
                lines[i] = f"PERIODIC_REPLY={new_value}\n"
                keyword_found = True
                break

        # If the keyword was not found, add it to the file
        if not keyword_found:
            lines.append("PERIODIC_REPLY=true\n")

        # Write the updated content back to the file
        with open(file_path, 'w') as file:
            file.writelines(lines)

        print("PERIODIC_REPLY value has been toggled successfully.")

    except Exception as e:
        print(f"An error occurred while toggling PERIODIC_REPLY: {e}")


@bot.event
async def on_message(message):
    
    if message.content.startswith("~preset"):
        append_to_json(message.content)
    if message.content.startswith("~clear"):
        clear_json_file()
    
    if message.content.startswith("~toggleRep"):
        toggle_periodic_reply("config/toogleReply.txt")
    
    if message.author== bot.user:
        print("self message")
        return
    
   
    if should_ignore_message(message) and not message.author.id == bot.owner_id:
        return
    

    if message.content.startswith(PREFIX):
        await bot.process_commands(message)
        return

    if is_trigger_message(message) and not bot.paused:
        print("trigger message")
        if message.reference and message.reference.resolved:
            if message.reference.resolved.author.id != bot.selfbot_id and (
                isinstance(message.channel, discord.DMChannel)
                or isinstance(message.channel, discord.GroupChannel)
            ):
                return

        for mention in message.mentions:
            message.content = message.content.replace(
                f"<@{mention.id}>", f"@{mention.display_name}"
            )

        author_id = str(message.author.id)
        update_message_history(author_id, message.content)

        if message.channel.id in bot.active_channels or (
            isinstance(message.channel, discord.GroupChannel) and bot.allow_gc
        ):
            key = f"{message.author.id}-{message.channel.id}"
            if key not in bot.message_history:
                bot.message_history[key] = []
            bot.message_history[key].append(
                {"role": "user", "content": message.content}
            )
            history = bot.message_history[key]

            prompt = message.content

            response = await generate_response_and_reply(message, prompt, history)
            bot.message_history[key].append({"role": "assistant", "content": response})


async def load_extensions():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
            except Exception as e:
                print(f"Failed to load extension {filename}. Error: {e}")


if __name__ == "__main__":
    asyncio.run(load_extensions())
    asyncio.run(bot.run(token=TOKEN, log_handler=None))
