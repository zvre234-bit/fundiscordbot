import discord
from discord.ext import commands, tasks
import os
from keep_alive import keep_alive
import random

# Sets up the bot with command prefix '!' and default intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# List of funny statuses for the bot to rotate through
status_list = [
    "touching grass",
    "losing at /mines",
    "judging your music taste",
    "currently AFK"
]

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    change_status.start() # Starts the status loop when the bot boots up

@tasks.loop(minutes=5)
async def change_status():
    # Picks a random status from the list and updates the bot
    new_status = random.choice(status_list)
    await bot.change_presence(activity=discord.Game(name=new_status))

@bot.command()
async def ping(ctx):
    await ctx.send('Pong! The bot is online.')

# Starts the web server, then runs the bot using the token from Render
keep_alive()
bot.run(os.environ.get('DISCORD_TOKEN'))
