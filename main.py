import discord
from discord.ext import commands, tasks
import os
import random
from keep_alive import keep_alive

# Sets up the bot with command prefix '!' and enables the intents you turned on
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 

bot = commands.Bot(command_prefix='!', intents=intents)

# List of funny statuses for the bot to rotate through
status_list = [
    "touching grass",
    "losing at !mines",
    "judging your music taste",
    "currently AFK"
]

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}!')
    if not change_status.is_running():
        change_status.start() # Starts the status loop when the bot boots up

@tasks.loop(minutes=5)
async def change_status():
    # Picks a random status from the list and updates the bot
    new_status = random.choice(status_list)
    await bot.change_presence(activity=discord.Game(name=new_status))

@bot.command()
async def ping(ctx):
    await ctx.send('Pong! The bot is online and ready for chaos.')

@bot.command()
async def afk(ctx, *, reason="touching grass"):
    # A simple AFK command setup
    await ctx.send(f'{ctx.author.mention} is now AFK. Reason: {reason}')

@bot.command()
async def mines(ctx):
    # A fun text-based minesweeper game using Discord's spoiler tags!
    grid = (
        "||💣|| ||💎|| ||💎||\n"
        "||💎|| ||💣|| ||💎||\n"
        "||💎|| ||💎|| ||💣||"
    )
    await ctx.send(f"Welcome to Mines, {ctx.author.mention}! Click the boxes at your own risk:\n\n{grid}")

# Starts the web server, then runs the bot using the token from Render
keep_alive()

# Fetches your secret token from Render's Environment Variables
bot.run(os.environ.get('DISCORD_TOKEN'))
