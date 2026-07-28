import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import random
import asyncio
import yt_dlp
from datetime import datetime, timedelta
from keep_alive import keep_alive

# Enable Privileged Gateway Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Sync the slash commands when the bot boots up
async def setup_hook():
    await bot.tree.sync()
    print("Slash commands synced globally!")
bot.setup_hook = setup_hook

# ==========================================
# JUMPSQUAD INITIALIZATION
# ==========================================
# Create 10 additional bot instances for the squad
squad_bots = [commands.Bot(command_prefix='!', intents=intents, help_command=None) for _ in range(10)]

# ==========================================
# DATABASES (Memory)
# ==========================================
user_balances = {}
user_inventory = {}
user_cooldowns = {}
quote_book = []
custom_playlists = {} # format: {user_id: {"playlist_name": ["url1", "url2"]}}

# Music States
server_repeat = {}
server_queues = {}
server_current_song = {}

# --- Economy Functions ---
def get_balance(user_id):
    if user_id not in user_balances:
        user_balances[user_id] = 1000 
    return user_balances[user_id]

def update_balance(user_id, amount):
    user_balances[user_id] = get_balance(user_id) + amount

def get_inventory(user_id):
    if user_id not in user_inventory:
        user_inventory[user_id] = {"padlock": 0, "skimask": 0, "nicktoken": 0}
    return user_inventory[user_id]

# ==========================================
# STATUS SETUP
# ==========================================
status_list = [
    "touching grass",
    "robbing your friends",
    "buying padlocks",
    "vibing to /lofi",
    "type /cmds for chaos"
]

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}!')
    if not change_status.is_running():
        change_status.start()

@tasks.loop(minutes=5)
async def change_status():
    new_status = random.choice(status_list)
    await bot.change_presence(activity=discord.Game(name=new_status))

# ==========================================
# UTILITY COMMANDS
# ==========================================
@bot.tree.command(name="cmds", description="Show the Mega Bot Command Menu")
async def cmds(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 Mega Bot Command Menu", color=discord.Color.purple())
    embed.add_field(name="🛠️ Utility", value="`/ping` - Check status\n`/afk [reason]` - Set AFK status", inline=False)
    embed.add_field(name="💰 Economy", value="`/bal` `/pay` `/rob` `/rich` `/daily`\n`/shop` `/buy` `/inv`", inline=False)
    embed.add_field(name="🤡 Chaos", value="`/quote add` `/quote random`\n`/vineboom` `/bruh`\n`/usenick [@user] [name]`", inline=False)
    embed.add_field(name="🎲 Casino", value="`/mines [bet] [bombs]`\n`/slots [bet]`\n`/coinflip [bet]`", inline=False)
    embed.add_field(name="🎧 Music & Voice", value="`/playsound [url]` `/playfile` `/pause` `/repeat`\n`/lofi` `/play_preset` `/playlist`\n`/afkbot` `/leave`\n`/jumpsquad [url]` `/jumpsquadfile` `/squadleave`", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="Check if the bot is alive")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message('Pong! The bot is online and ready for chaos.')

@bot.tree.command(name="afk", description="Set your status to AFK")
@app_commands.describe(reason="Why are you AFK?")
async def afk(interaction: discord.Interaction, reason: str = "touching grass"):
    await interaction.response.send_message(f'{interaction.user.mention} is now AFK. Reason: {reason}')

# ==========================================
# THE SHOP & DAILY REWARDS
# ==========================================
shop_items = {
    "padlock": {"price": 200, "desc": "Blocks one /rob attempt against you.", "icon": "🔒"},
    "skimask": {"price": 500, "desc": "Increases your chance to pull off a /rob.", "icon": "🎿"},
    "nicktoken": {"price": 2000, "desc": "Change a friend's nickname (/usenick).", "icon": "🏷️"}
}

@bot.tree.command(name="shop", description="Open the Black Market")
async def shop(interaction: discord.Interaction):
    embed = discord.Embed(title="🛒 The Black Market", color=discord.Color.green())
    for item, data in shop_items.items():
        embed.add_field(name=f"{data['icon']} {item.capitalize()} - {data['price']} coins", value=data['desc'], inline=False)
    embed.set_footer(text="Use /buy [item] to purchase.")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="buy", description="Buy an item from the shop")
async def buy(interaction: discord.Interaction, item: str):
    item = item.lower()
    if item not in shop_items:
        return await interaction.response.send_message("❌ That item doesn't exist in the shop.", ephemeral=True)
    
    price = shop_items[item]["price"]
    if get_balance(interaction.user.id) < price:
        return await interaction.response.send_message("❌ You're too broke to buy this.", ephemeral=True)
    
    update_balance(interaction.user.id, -price)
    inv = get_inventory(interaction.user.id)
    inv[item] += 1
    await interaction.response.send_message(f"✅ You bought a {shop_items[item]['icon']} **{item.capitalize()}** for {price} coins!")

@bot.tree.command(name="inv", description="Check your inventory")
async def inv(interaction: discord.Interaction):
    inv = get_inventory(interaction.user.id)
    text = "\n".join([f"{shop_items[k]['icon']} {k.capitalize()}: {v}" for k, v in inv.items() if v > 0])
    if not text:
        text = "Your inventory is completely empty. Go buy something!"
    embed = discord.Embed(title=f"🎒 {interaction.user.name}'s Inventory", description=text, color=discord.Color.gold())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="daily", description="Claim your daily coins")
async def daily(interaction: discord.Interaction):
    last_claimed = user_cooldowns.get(interaction.user.id)
    now = datetime.now()
    
    if last_claimed and now < last_claimed + timedelta(hours=24):
        remaining = (last_claimed + timedelta(hours=24)) - now
        hours, remainder = divmod(remaining.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        return await interaction.response.send_message(f"⏳ You already claimed your daily! Come back in **{hours}h {minutes}m**.", ephemeral=True)
    
    user_cooldowns[interaction.user.id] = now
    reward = random.randint(300, 700)
    update_balance(interaction.user.id, reward)
    await interaction.response.send_message(f"🎁 {interaction.user.mention} claimed their daily reward and got **{reward} coins**!")

@bot.tree.command(name="usenick", description="Use a Nickname Token on a friend")
async def usenick(interaction: discord.Interaction, member: discord.Member, new_nick: str):
    inv = get_inventory(interaction.user.id)
    if inv["nicktoken"] < 1:
        return await interaction.response.send_message("❌ You don't own a Nickname Token! Buy one in the /shop.", ephemeral=True)
    
    try:
        await member.edit(nick=new_nick[:32])
        inv["nicktoken"] -= 1
        await interaction.response.send_message(f"🏷️ Success! {interaction.user.mention} used a token to change {member.name}'s nickname.")
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to change that user's nickname.", ephemeral=True)

# ==========================================
# ECONOMY & ROBBING 
# ==========================================
@bot.tree.command(name="bal", description="Check your coin balance")
async def bal(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    coins = get_balance(target.id)
    await interaction.response.send_message(f"💰 {target.mention} currently has **{coins} coins**.")

@bot.tree.command(name="pay", description="Pay a friend some coins")
async def pay(interaction: discord.Interaction, member: discord.Member, amount: int):
    if amount <= 0:
        return await interaction.response.send_message("❌ You must pay at least 1 coin.", ephemeral=True)
    if get_balance(interaction.user.id) < amount:
        return await interaction.response.send_message("❌ You don't have enough coins for that!", ephemeral=True)
    if member.id == interaction.user.id:
        return await interaction.response.send_message("❌ You can't pay yourself!", ephemeral=True)

    update_balance(interaction.user.id, -amount)
    update_balance(member.id, amount)
    await interaction.response.send_message(f"💸 {interaction.user.mention} successfully paid {member.mention} **{amount} coins**!")

@bot.tree.command(name="rich", description="Show the server wealth leaderboard")
async def rich(interaction: discord.Interaction):
    sorted_balances = sorted(user_balances.items(), key=lambda item: item[1], reverse=True)
    embed = discord.Embed(title="🏆 Richest Players", color=discord.Color.gold())
    board = ""
    for index, (user_id, balance) in enumerate(sorted_balances[:5]):
        user = bot.get_user(user_id)
        username = user.name if user else f"Unknown User ({user_id})"
        board += f"**{index + 1}.** {username} - 💰 {balance}\n"
    embed.description = board if board else "Nobody has any money yet!"
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="rob", description="Attempt to rob a friend")
async def rob(interaction: discord.Interaction, member: discord.Member):
    if member.id == interaction.user.id:
        return await interaction.response.send_message("❌ You can't rob yourself!", ephemeral=True)
    if get_balance(member.id) < 50:
        return await interaction.response.send_message("❌ They are too poor to rob right now.", ephemeral=True)
    if get_balance(interaction.user.id) < 50:
        return await interaction.response.send_message("❌ You need at least 50 coins to cover the fine if you get caught!", ephemeral=True)

    target_inv = get_inventory(member.id)
    if target_inv["padlock"] > 0:
        target_inv["padlock"] -= 1
        return await interaction.response.send_message(f"🔒 **BLOCKED!** {interaction.user.mention} tried to rob {member.mention}, but they had a Padlock! The padlock broke.")

    robber_inv = get_inventory(interaction.user.id)
    chance = 0.60 if robber_inv["skimask"] > 0 else 0.40

    if random.random() < chance:
        steal_amount = random.randint(10, int(get_balance(member.id) * 0.3))
        update_balance(member.id, -steal_amount)
        update_balance(interaction.user.id, steal_amount)
        if robber_inv["skimask"] > 0:
            robber_inv["skimask"] -= 1
            await interaction.response.send_message(f"🥷 **SUCCESS!** {interaction.user.mention} used a Ski Mask and snuck away with **{steal_amount} coins** from {member.mention}! (Mask broke)")
        else:
            await interaction.response.send_message(f"🥷 **SUCCESS!** {interaction.user.mention} snuck away with **{steal_amount} coins** from {member.mention}!")
    else:
        fine = 50
        update_balance(interaction.user.id, -fine)
        update_balance(member.id, fine)
        if robber_inv["skimask"] > 0:
            robber_inv["skimask"] -= 1
        await interaction.response.send_message(f"🚨 **BUSTED!** {interaction.user.mention} got caught trying to rob {member.mention} and paid a **{fine} coin** fine!")

# ==========================================
# THE QUOTE BOOK (HALL OF SHAME)
# ==========================================
quote_group = app_commands.Group(name="quote", description="Quote book commands")

@quote_group.command(name="add", description="Add a stupid quote to the Hall of Shame")
async def quote_add(interaction: discord.Interaction, text: str):
    quote_book.append(f'"{text}" - added by {interaction.user.name}')
    await interaction.response.send_message("✍️ Added to the Hall of Shame.")

@quote_group.command(name="random", description="Pull a random quote from the Hall of Shame")
async def quote_random(interaction: discord.Interaction):
    if not quote_book:
        return await interaction.response.send_message("The quote book is empty!", ephemeral=True)
    await interaction.response.send_message(random.choice(quote_book))

bot.tree.add_command(quote_group)

# ==========================================
# HIT-AND-RUN SOUNDBOARDS
# ==========================================
async def play_local_sound(interaction: discord.Interaction, filename: str):
    if not interaction.user.voice:
        return await interaction.response.send_message("❌ You need to be in a voice channel first!", ephemeral=True)
    
    channel = interaction.user.voice.channel
    await interaction.response.send_message(f"🔊 Playing {filename}...", ephemeral=True)
    
    try:
        voice_client = interaction.guild.voice_client
        if not voice_client:
            voice_client = await channel.connect()
        elif voice_client.channel != channel:
            await voice_client.move_to(channel)

        if voice_client.is_playing():
            voice_client.stop()

        voice_client.play(discord.FFmpegPCMAudio(f"sounds/{filename}"))
        
        while voice_client.is_playing():
            await asyncio.sleep(1)
            
        await voice_client.disconnect()
    except Exception as e:
        await interaction.followup.send(f"Audio error: {e}", ephemeral=True)

@bot.tree.command(name="vineboom", description="Hit-and-run Vine Boom sound")
async def vineboom(interaction: discord.Interaction):
    await play_local_sound(interaction, "vineboom.mp3")

@bot.tree.command(name="bruh", description="Hit-and-run Bruh sound")
async def bruh(interaction: discord.Interaction):
    await play_local_sound(interaction, "bruh.mp3")

# ==========================================
# MUSIC & VOICE STREAMING
# ==========================================
YTDL_OPTS = {
    'format': 'bestaudio/best',
    'noplaylist': 'True',
    'quiet': True,
    'no_warnings': True,
    'cookiefile': 'cookies.txt',
}
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

def check_queue(error, guild_id, channel):
    """Called after a song finishes to handle repeating or queues."""
    # This is called in a separate thread by FFmpeg, so we use threadsafe calls if we need to do async stuff.
    pass # Kept simple to avoid blocking FFmpeg.

async def core_stream_audio(interaction: discord.Interaction, url: str, channel: discord.VoiceChannel = None, is_file=False):
    if not channel:
        channel = interaction.user.voice.channel

    try:
        vc = interaction.guild.voice_client
        if not vc:
            vc = await channel.connect()
        elif vc.channel != channel:
            await vc.move_to(channel)

        if vc.is_playing() or vc.is_paused():
            vc.stop()

        audio_url = url
        title = "Uploaded File" if is_file else "Unknown Audio"

        if not is_file:
            with yt_dlp.YoutubeDL(YTDL_OPTS) as ydl:
                loop = asyncio.get_event_loop()
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
                audio_url = info['url']
                title = info.get('title', 'Unknown Audio')

        # Create a looping stream if repeat is enabled
        def after_playing(e):
            if server_repeat.get(interaction.guild.id, False):
                # We need to reconnect the audio stream to repeat
                coro = core_stream_audio(interaction, url, channel, is_file)
                asyncio.run_coroutine_threadsafe(coro, bot.loop)

        vc.play(discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS), after=after_playing)
        server_current_song[interaction.guild.id] = {"url": url, "is_file": is_file, "title": title}
        
        await interaction.followup.send(f"🎶 **Now Playing:** {title}")

    except Exception as e:
        await interaction.followup.send(f"❌ Error playing audio: {e}")

@bot.tree.command(name="playsound", description="Stream audio from a URL")
async def playsound(interaction: discord.Interaction, url: str):
    if not interaction.user.voice:
        return await interaction.response.send_message("❌ Join a voice channel first!", ephemeral=True)
    await interaction.response.defer()
    await core_stream_audio(interaction, url)

@bot.tree.command(name="playfile", description="Upload an MP3/MP4 file to play in your voice channel")
async def playfile(interaction: discord.Interaction, file: discord.Attachment):
    if not interaction.user.voice:
        return await interaction.response.send_message("❌ You need to be in a voice channel first!", ephemeral=True)
    await interaction.response.defer()
    await core_stream_audio(interaction, file.url, is_file=True)

@bot.tree.command(name="pause", description="Pause or resume the current music")
async def pause_music(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc:
        return await interaction.response.send_message("❌ I'm not in a voice channel.", ephemeral=True)
    
    if vc.is_paused():
        vc.resume()
        await interaction.response.send_message("▶️ Resumed the music.")
    elif vc.is_playing():
        vc.pause()
        await interaction.response.send_message("⏸️ Paused the music.")
    else:
        await interaction.response.send_message("❌ Nothing is playing.", ephemeral=True)

@bot.tree.command(name="repeat", description="Toggle repeating the current song")
async def repeat_music(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    is_repeating = server_repeat.get(guild_id, False)
    server_repeat[guild_id] = not is_repeating
    
    if not is_repeating:
        await interaction.response.send_message("🔁 **Repeat is ON.** The current song will loop.")
    else:
        await interaction.response.send_message("➡️ **Repeat is OFF.**")

@bot.tree.command(name="lofi", description="Play the 24/7 Lofi Girl Stream")
async def lofi(interaction: discord.Interaction):
    if not interaction.user.voice:
        return await interaction.response.send_message("❌ Join a voice channel first!", ephemeral=True)
    await interaction.response.defer()
    await core_stream_audio(interaction, "https://www.youtube.com/watch?v=jfKfPfyJRdk")

@bot.tree.command(name="afkbot", description="Send the bot to the AFK channel with Lofi")
async def afkbot(interaction: discord.Interaction):
    TARGET_VC_ID = 1527215057174532260
    target_channel = bot.get_channel(TARGET_VC_ID)
    
    if not target_channel:
        return await interaction.response.send_message("❌ I couldn't find the VC with that ID! Make sure I have permissions to see it.", ephemeral=True)
    
    await interaction.response.defer()
    await interaction.followup.send("🤖 `Engaging AFK Bot Protocol. Moving to AFK VC...`")
    await core_stream_audio(interaction, "https://www.youtube.com/watch?v=jfKfPfyJRdk", channel=target_channel)

@bot.tree.command(name="leave", description="Disconnect the bot from voice")
async def leave(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        server_repeat[interaction.guild.id] = False
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("👋 Disconnected from the voice channel.")
    else:
        await interaction.response.send_message("❌ I'm not in a voice channel right now.", ephemeral=True)

# ==========================================
# CUSTOM PLAYLISTS
# ==========================================
playlist_group = app_commands.Group(name="playlist", description="Manage and play custom playlists")

@playlist_group.command(name="create", description="Create a new custom playlist")
async def pl_create(interaction: discord.Interaction, name: str):
    user_id = interaction.user.id
    if user_id not in custom_playlists:
        custom_playlists[user_id] = {}
    
    if name in custom_playlists[user_id]:
        return await interaction.response.send_message(f"❌ You already have a playlist named `{name}`.", ephemeral=True)
        
    custom_playlists[user_id][name] = []
    await interaction.response.send_message(f"✅ Created new empty playlist: **{name}**. Use `/playlist add` to add songs!")

@playlist_group.command(name="add", description="Add a URL or File to your playlist")
async def pl_add(interaction: discord.Interaction, name: str, url: str = None, file: discord.Attachment = None):
    user_id = interaction.user.id
    if user_id not in custom_playlists or name not in custom_playlists[user_id]:
        return await interaction.response.send_message(f"❌ You don't have a playlist named `{name}`.", ephemeral=True)
        
    if not url and not file:
        return await interaction.response.send_message("❌ You must provide either a URL or an uploaded File.", ephemeral=True)
        
    entry = {"url": url if url else file.url, "is_file": file is not None}
    custom_playlists[user_id][name].append(entry)
    
    msg = f"✅ Added song to **{name}**!"
    if file:
        msg += "\n*(⚠️ Warning: Discord file attachments expire after 24h, so this saved file will only work today!)*"
    await interaction.response.send_message(msg)

@playlist_group.command(name="play", description="Play a saved playlist")
async def pl_play(interaction: discord.Interaction, name: str):
    user_id = interaction.user.id
    if user_id not in custom_playlists or name not in custom_playlists[user_id]:
        return await interaction.response.send_message(f"❌ You don't have a playlist named `{name}`.", ephemeral=True)
        
    playlist = custom_playlists[user_id][name]
    if not playlist:
        return await interaction.response.send_message("❌ That playlist is empty!", ephemeral=True)
        
    if not interaction.user.voice:
        return await interaction.response.send_message("❌ Join a voice channel first!", ephemeral=True)
        
    await interaction.response.defer()
    await interaction.followup.send(f"🎧 Starting custom playlist: **{name}** ({len(playlist)} songs). Note: Beta bot will just play the first song on loop if /repeat is on, full queue logic requires a bigger server.")
    
    # Play the first song for now to keep it simple in a 1-file script
    first_song = playlist[0]
    await core_stream_audio(interaction, first_song["url"], is_file=first_song["is_file"])

bot.tree.add_command(playlist_group)

@bot.tree.command(name="play_preset", description="Play a built-in preset playlist")
@app_commands.describe(preset="Choose hype, gaming, or chill")
async def play_preset(interaction: discord.Interaction, preset: str):
    presets = {
        "hype": "https://www.youtube.com/watch?v=aGjtEXUqObI",
        "gaming": "https://www.youtube.com/watch?v=1tGhhz8ExQk",
        "chill": "https://www.youtube.com/watch?v=jfKfPfyJRdk"
    }
    
    if preset.lower() not in presets:
        options = ", ".join(presets.keys())
        return await interaction.response.send_message(f"🎧 Choose a preset: `{options}`", ephemeral=True)
        
    if not interaction.user.voice:
        return await interaction.response.send_message("❌ Join a voice channel first!", ephemeral=True)
        
    await interaction.response.defer()
    await core_stream_audio(interaction, presets[preset.lower()])


# ==========================================
# JUMPSQUAD COMMANDS
# ==========================================
async def core_jumpsquad(interaction: discord.Interaction, url: str, is_file=False):
    if not interaction.user.voice:
        return await interaction.response.send_message("❌ You need to be in a voice channel first!", ephemeral=True)
    
    channel = interaction.user.voice.channel
    await interaction.response.defer()
    msg = await interaction.followup.send("🚨 **DEPLOYING THE JUMPSQUAD (11 BOTS MAX)** 🚨\n`Extracting audio...`", wait=True)

    audio_url = url
    title = "Uploaded File" if is_file else "Unknown Audio"

    if not is_file:
        try:
            with yt_dlp.YoutubeDL(YTDL_OPTS) as ydl:
                loop = asyncio.get_event_loop()
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
                audio_url = info['url']
                title = info.get('title', 'Unknown Audio')
        except Exception as e:
            return await msg.edit(content=f"❌ Error extracting audio: {e}")

    await msg.edit(content=f"🎶 **Target Locked:** {title}\n`Deploying 11-bot squad to VC...`")

    all_bots = [bot] + squad_bots
    connected_vcs = []

    for b in all_bots:
        try:
            if not b.is_ready(): 
                continue

            b_channel = b.get_channel(channel.id) or await b.fetch_channel(channel.id)
            vc = discord.utils.get(b.voice_clients, guild=b_channel.guild)
            
            if not vc:
                vc = await b_channel.connect()
            elif vc.channel != b_channel:
                await vc.move_to(b_channel)

            if vc.is_playing():
                vc.stop()
                
            connected_vcs.append(vc)
            await asyncio.sleep(0.5) 
            
        except Exception as e:
            print(f"Bot {b.user} failed to join: {e}")

    await msg.edit(content=f"🔊 **VC BREACHED** 🔊\n`Synchronizing audio across {len(connected_vcs)} bots...`")

    audio_sources = []
    for _ in connected_vcs:
        audio_sources.append(discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS))

    for i, vc in enumerate(connected_vcs):
        try:
            vc.play(audio_sources[i])
        except Exception as e:
            print(f"Failed to play on bot {vc.client.user}: {e}")

    await msg.edit(content=f"🔊 **JUMPSQUAD FULLY DEPLOYED** 🔊\nNow playing **{title}** on {len(connected_vcs)} bots simultaneously!")

@bot.tree.command(name="jumpsquad", description="Deploy the Jumpsquad with a URL")
async def jumpsquad_url(interaction: discord.Interaction, url: str):
    await core_jumpsquad(interaction, url, is_file=False)

@bot.tree.command(name="jumpsquadfile", description="Deploy the Jumpsquad with an uploaded File")
async def jumpsquad_file(interaction: discord.Interaction, file: discord.Attachment):
    await core_jumpsquad(interaction, file.url, is_file=True)

@bot.tree.command(name="squadleave", description="Recall the Jumpsquad")
async def squadleave(interaction: discord.Interaction):
    all_bots = [bot] + squad_bots
    disconnected = 0
    for b in all_bots:
        if not b.is_ready():
            continue
        vc = discord.utils.get(b.voice_clients, guild=interaction.guild)
        if vc:
            await vc.disconnect()
            disconnected += 1
    
    if disconnected > 0:
        await interaction.response.send_message(f"👋 Recalled the Jumpsquad. Disconnected {disconnected} bots.")
    else:
        await interaction.response.send_message("❌ The Jumpsquad isn't in any voice channels.", ephemeral=True)


# ==========================================
# INTERACTIVE GAMES (UI VIEWS)
# ==========================================
class CoinflipView(discord.ui.View):
    def __init__(self, author, bet):
        super().__init__(timeout=60)
        self.author = author
        self.bet = bet

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message("🛑 Hands off! This isn't your coinflip.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Heads", style=discord.ButtonStyle.primary, emoji="🪙")
    async def heads(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.resolve_flip(interaction, "heads")

    @discord.ui.button(label="Tails", style=discord.ButtonStyle.primary, emoji="🪙")
    async def tails(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.resolve_flip(interaction, "tails")

    async def resolve_flip(self, interaction, choice):
        outcome = random.choice(['heads', 'tails'])
        if choice == outcome:
            update_balance(self.author.id, self.bet)
            msg = f"🎉 The coin landed on **{outcome}**! {self.author.mention} won **{self.bet} coins**!"
        else:
            update_balance(self.author.id, -self.bet)
            msg = f"💀 The coin landed on **{outcome}**. {self.author.mention} lost **{self.bet} coins**."
        
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content=msg, view=self)
        self.stop()

@bot.tree.command(name="coinflip", description="Bet coins on a coinflip")
async def coinflip(interaction: discord.Interaction, bet: int):
    if bet <= 0 or bet > get_balance(interaction.user.id):
        return await interaction.response.send_message("❌ Invalid bet amount! Check your balance.", ephemeral=True)
    view = CoinflipView(interaction.user, bet)
    await interaction.response.send_message(f"🪙 {interaction.user.mention} is betting **{bet} coins**. Choose Heads or Tails!", view=view)

class SlotsView(discord.ui.View):
    def __init__(self, author, bet):
        super().__init__(timeout=60)
        self.author = author
        self.bet = bet

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message("🛑 Find your own slot machine!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🎰 SPIN!", style=discord.ButtonStyle.success)
    async def spin(self, interaction: discord.Interaction, button: discord.ui.Button):
        emojis = ["🍒", "🍋", "🍉", "⭐", "💎"]
        slot1, slot2, slot3 = random.choice(emojis), random.choice(emojis), random.choice(emojis)
        
        res = f"| {slot1} | {slot2} | {slot3} |\n"
        if slot1 == slot2 == slot3:
            winnings = self.bet * 5
            update_balance(self.author.id, winnings)
            res += f"JACKPOT! 🏆 {self.author.mention} won **{winnings} coins**!"
        elif slot1 == slot2 or slot2 == slot3 or slot1 == slot3:
            winnings = int(self.bet * 1.5)
            update_balance(self.author.id, winnings)
            res += f"Small win! 🎉 {self.author.mention} won **{winnings} coins**."
        else:
            update_balance(self.author.id, -self.bet)
            res += f"{self.author.mention} lost **{self.bet} coins**. RIP."
            
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content=f"🎰 **SLOTS** 🎰\n{res}", view=self)
        self.stop()

@bot.tree.command(name="slots", description="Bet coins on the slot machine")
async def slots(interaction: discord.Interaction, bet: int):
    if bet <= 0 or bet > get_balance(interaction.user.id):
        return await interaction.response.send_message("❌ Invalid bet amount! Check your balance.", ephemeral=True)
    view = SlotsView(interaction.user, bet)
    await interaction.response.send_message(f"🎰 {interaction.user.mention} is playing slots for **{bet} coins**!", view=view)

class MineButton(discord.ui.Button):
    def __init__(self, is_bomb, x, y):
        super().__init__(style=discord.ButtonStyle.secondary, label="❓", row=y)
        self.is_bomb = is_bomb

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if self.is_bomb:
            update_balance(view.author.id, -view.bet)
            for child in view.children:
                child.disabled = True
                if isinstance(child, MineButton) and child.is_bomb:
                    child.style = discord.ButtonStyle.danger
                    child.emoji = "💣"
                    child.label = ""
            
            embed = interaction.message.embeds[0]
            embed.description = f"💥 BOOM! {view.author.mention} hit a mine and lost **{view.bet} coins**!"
            embed.color = discord.Color.red()
            await interaction.response.edit_message(embed=embed, view=view)
            view.stop()
        else:
            self.style = discord.ButtonStyle.success
            self.emoji = "💎"
            self.label = ""
            self.disabled = True
            view.safe_clicks += 1
            
            multiplier = 1.0 + (view.safe_clicks * (view.bomb_count * 0.1))
            view.current_winnings = int(view.bet * multiplier)
            
            embed = interaction.message.embeds[0]
            embed.description = f"Safe! 💎 {view.author.mention}'s current winnings: **{view.current_winnings} coins**.\nKeep clicking or Cash Out!"
            await interaction.response.edit_message(embed=embed, view=view)

class MinesView(discord.ui.View):
    def __init__(self, author, bet, bomb_count):
        super().__init__(timeout=120)
        self.author = author
        self.bet = bet
        self.bomb_count = bomb_count
        self.safe_clicks = 0
        self.current_winnings = bet
        
        tiles = [True]*bomb_count + [False]*(16 - bomb_count)
        random.shuffle(tiles)
        
        for i, is_bomb in enumerate(tiles):
            self.add_item(MineButton(is_bomb, x=i%4, y=i//4))
            
        cashout = discord.ui.Button(style=discord.ButtonStyle.primary, label="💰 Cash Out", row=4)
        cashout.callback = self.cash_out
        self.add_item(cashout)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            await interaction.response.send_message("🛑 Hands off! This isn't your minefield.", ephemeral=True)
            return False
        return True

    async def cash_out(self, interaction: discord.Interaction):
        if self.safe_clicks == 0:
            await interaction.response.send_message("You need to click at least one safe tile to cash out!", ephemeral=True)
            return
            
        profit = self.current_winnings - self.bet
        update_balance(self.author.id, profit)
        for child in self.children:
            child.disabled = True
            
        embed = interaction.message.embeds[0]
        embed.description = f"🏃 {self.author.mention} cashed out and walked away with **{self.current_winnings} coins**!"
        embed.color = discord.Color.green()
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

@bot.tree.command(name="mines", description="Play a game of mines")
async def mines(interaction: discord.Interaction, bet: int, bombs: int = 4):
    if bet <= 0 or bet > get_balance(interaction.user.id):
        return await interaction.response.send_message("❌ Invalid bet amount! Check your balance.", ephemeral=True)
    if bombs < 1 or bombs > 15:
        return await interaction.response.send_message("❌ You must choose between 1 and 15 bombs.", ephemeral=True)
    
    view = MinesView(interaction.user, bet, bombs)
    embed = discord.Embed(title=f"🧨 Minefield ({bombs} Bombs)", color=discord.Color.blue())
    embed.description = f"{interaction.user.mention} is playing for **{bet} coins**!\nClick the tiles to find gems 💎 and avoid the bombs 💣."
    await interaction.response.send_message(embed=embed, view=view)


# ==========================================
# SERVER KEEP-ALIVE & BOOT
# ==========================================
async def start_all_bots():
    squad_tokens = [os.environ.get(f'SQUAD_TOKEN_{i}') for i in range(1, 11)]
    tasks = [bot.start(os.environ.get('DISCORD_TOKEN'))]
    
    for i, s_bot in enumerate(squad_bots):
        if squad_tokens[i]:
            tasks.append(s_bot.start(squad_tokens[i]))
        else:
            print(f"⚠️ Warning: SQUAD_TOKEN_{i+1} is missing in Render! That bot won't boot.")

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    keep_alive()
    asyncio.run(start_all_bots())
