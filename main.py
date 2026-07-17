import discord
from discord.ext import commands, tasks
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

# ==========================================
# JUMPSQUAD INITIALIZATION
# ==========================================
# Create 4 additional bot instances for the squad
squad_bots = [commands.Bot(command_prefix='!', intents=intents, help_command=None) for _ in range(4)]

# ==========================================
# DATABASES (Memory)
# ==========================================
user_balances = {}
user_inventory = {}
user_cooldowns = {}
quote_book = []

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
    "vibing to !lofi",
    "type !cmds for chaos"
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
@bot.command()
async def cmds(ctx):
    embed = discord.Embed(title="🤖 Mega Bot Command Menu", color=discord.Color.purple())
    embed.add_field(name="🛠️ Utility", value="`!ping` - Check status\n`!afk [reason]` - Set AFK status", inline=False)
    embed.add_field(name="💰 Economy", value="`!bal` `!pay` `!rob` `!rich` `!daily`\n`!shop` `!buy` `!inv`", inline=False)
    embed.add_field(name="🤡 Chaos", value="`!quote add` `!quote random`\n`!vineboom` `!bruh`\n`!usenick [@user] [name]`", inline=False)
    embed.add_field(name="🎲 Casino", value="`!mines [bet] [bombs]`\n`!slots [bet]`\n`!coinflip [bet]`", inline=False)
    embed.add_field(name="🎧 Music & Voice", value="`!playsound [url]` `!lofi` `!playlist [name]`\n`!afkbot` `!leave`\n`!jumpsquad [url]` `!squadleave`", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    await ctx.send('Pong! The bot is online and ready for chaos.')

@bot.command()
async def afk(ctx, *, reason="touching grass"):
    await ctx.send(f'{ctx.author.mention} is now AFK. Reason: {reason}')

# ==========================================
# THE SHOP & DAILY REWARDS
# ==========================================
shop_items = {
    "padlock": {"price": 200, "desc": "Blocks one !rob attempt against you.", "icon": "🔒"},
    "skimask": {"price": 500, "desc": "Increases your chance to pull off a !rob.", "icon": "🎿"},
    "nicktoken": {"price": 2000, "desc": "Change a friend's nickname (!usenick).", "icon": "🏷️"}
}

@bot.command()
async def shop(ctx):
    embed = discord.Embed(title="🛒 The Black Market", color=discord.Color.green())
    for item, data in shop_items.items():
        embed.add_field(name=f"{data['icon']} {item.capitalize()} - {data['price']} coins", value=data['desc'], inline=False)
    embed.set_footer(text="Use !buy [item] to purchase.")
    await ctx.send(embed=embed)

@bot.command()
async def buy(ctx, item: str):
    item = item.lower()
    if item not in shop_items:
        return await ctx.send("❌ That item doesn't exist in the shop.")
    
    price = shop_items[item]["price"]
    if get_balance(ctx.author.id) < price:
        return await ctx.send("❌ You're too broke to buy this.")
    
    update_balance(ctx.author.id, -price)
    inv = get_inventory(ctx.author.id)
    inv[item] += 1
    await ctx.send(f"✅ You bought a {shop_items[item]['icon']} **{item.capitalize()}** for {price} coins!")

@bot.command()
async def inv(ctx):
    inv = get_inventory(ctx.author.id)
    text = "\n".join([f"{shop_items[k]['icon']} {k.capitalize()}: {v}" for k, v in inv.items() if v > 0])
    if not text:
        text = "Your inventory is completely empty. Go buy something!"
    embed = discord.Embed(title=f"🎒 {ctx.author.name}'s Inventory", description=text, color=discord.Color.gold())
    await ctx.send(embed=embed)

@bot.command()
async def daily(ctx):
    last_claimed = user_cooldowns.get(ctx.author.id)
    now = datetime.now()
    
    if last_claimed and now < last_claimed + timedelta(hours=24):
        remaining = (last_claimed + timedelta(hours=24)) - now
        hours, remainder = divmod(remaining.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        return await ctx.send(f"⏳ You already claimed your daily! Come back in **{hours}h {minutes}m**.")
    
    user_cooldowns[ctx.author.id] = now
    reward = random.randint(300, 700)
    update_balance(ctx.author.id, reward)
    await ctx.send(f"🎁 {ctx.author.mention} claimed their daily reward and got **{reward} coins**!")

@bot.command()
async def usenick(ctx, member: discord.Member, *, new_nick: str):
    inv = get_inventory(ctx.author.id)
    if inv["nicktoken"] < 1:
        return await ctx.send("❌ You don't own a Nickname Token! Buy one in the !shop.")
    
    try:
        await member.edit(nick=new_nick[:32])
        inv["nicktoken"] -= 1
        await ctx.send(f"🏷️ Success! {ctx.author.mention} used a token to change {member.name}'s nickname.")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change that user's nickname.")

# ==========================================
# ECONOMY & ROBBING 
# ==========================================
@bot.command(aliases=['balance', 'coins'])
async def bal(ctx, member: discord.Member = None):
    target = member or ctx.author
    coins = get_balance(target.id)
    await ctx.send(f"💰 {target.mention} currently has **{coins} coins**.")

@bot.command()
async def pay(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        return await ctx.send("❌ You must pay at least 1 coin.")
    if get_balance(ctx.author.id) < amount:
        return await ctx.send("❌ You don't have enough coins for that!")
    if member.id == ctx.author.id:
        return await ctx.send("❌ You can't pay yourself!")

    update_balance(ctx.author.id, -amount)
    update_balance(member.id, amount)
    await ctx.send(f"💸 {ctx.author.mention} successfully paid {member.mention} **{amount} coins**!")

@bot.command(aliases=['leaderboard', 'top'])
async def rich(ctx):
    sorted_balances = sorted(user_balances.items(), key=lambda item: item[1], reverse=True)
    embed = discord.Embed(title="🏆 Richest Players", color=discord.Color.gold())
    board = ""
    for index, (user_id, balance) in enumerate(sorted_balances[:5]):
        user = bot.get_user(user_id)
        username = user.name if user else f"Unknown User ({user_id})"
        board += f"**{index + 1}.** {username} - 💰 {balance}\n"
    embed.description = board if board else "Nobody has any money yet!"
    await ctx.send(embed=embed)

@bot.command()
async def rob(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        return await ctx.send("❌ You can't rob yourself!")
    if get_balance(member.id) < 50:
        return await ctx.send("❌ They are too poor to rob right now.")
    if get_balance(ctx.author.id) < 50:
        return await ctx.send("❌ You need at least 50 coins to cover the fine if you get caught!")

    target_inv = get_inventory(member.id)
    if target_inv["padlock"] > 0:
        target_inv["padlock"] -= 1
        return await ctx.send(f"🔒 **BLOCKED!** {ctx.author.mention} tried to rob {member.mention}, but they had a Padlock! The padlock broke.")

    robber_inv = get_inventory(ctx.author.id)
    chance = 0.60 if robber_inv["skimask"] > 0 else 0.40

    if random.random() < chance:
        steal_amount = random.randint(10, int(get_balance(member.id) * 0.3))
        update_balance(member.id, -steal_amount)
        update_balance(ctx.author.id, steal_amount)
        if robber_inv["skimask"] > 0:
            robber_inv["skimask"] -= 1
            await ctx.send(f"🥷 **SUCCESS!** {ctx.author.mention} used a Ski Mask and snuck away with **{steal_amount} coins** from {member.mention}! (Mask broke)")
        else:
            await ctx.send(f"🥷 **SUCCESS!** {ctx.author.mention} snuck away with **{steal_amount} coins** from {member.mention}!")
    else:
        fine = 50
        update_balance(ctx.author.id, -fine)
        update_balance(member.id, fine)
        if robber_inv["skimask"] > 0:
            robber_inv["skimask"] -= 1
        await ctx.send(f"🚨 **BUSTED!** {ctx.author.mention} got caught trying to rob {member.mention} and paid a **{fine} coin** fine!")

# ==========================================
# THE QUOTE BOOK (HALL OF SHAME)
# ==========================================
@bot.group(invoke_without_command=True)
async def quote(ctx):
    await ctx.send("Use `!quote add [quote]` or `!quote random`.")

@quote.command()
async def add(ctx, *, text: str):
    quote_book.append(f'"{text}" - added by {ctx.author.name}')
    await ctx.send("✍️ Added to the Hall of Shame.")

@quote.command()
async def random_quote(ctx):
    if not quote_book:
        return await ctx.send("The quote book is empty!")
    await ctx.send(random.choice(quote_book))

# ==========================================
# HIT-AND-RUN SOUNDBOARDS
# ==========================================
async def play_local_sound(ctx, filename):
    if not ctx.author.voice:
        return await ctx.send("❌ You need to be in a voice channel first!")
    
    channel = ctx.author.voice.channel
    try:
        voice_client = ctx.voice_client
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
        await ctx.send(f"Audio error: {e}")

@bot.command()
async def vineboom(ctx):
    await play_local_sound(ctx, "vineboom.mp3")

@bot.command()
async def bruh(ctx):
    await play_local_sound(ctx, "bruh.mp3")

# ==========================================
# MUSIC & VOICE STREAMING
# ==========================================
# Setup yt-dlp to stream audio instead of downloading it
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

async def stream_audio(ctx, url, channel=None):
    if not channel:
        if not ctx.author.voice:
            return await ctx.send("❌ Join a voice channel first!")
        channel = ctx.author.voice.channel

    try:
        vc = ctx.voice_client
        if not vc:
            vc = await channel.connect()
        elif vc.channel != channel:
            await vc.move_to(channel)

        if vc.is_playing():
            vc.stop()

        msg = await ctx.send("🔍 `Loading audio stream...`")
        
        # Run yt-dlp extract in background to avoid freezing the bot
        with yt_dlp.YoutubeDL(YTDL_OPTS) as ydl:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
            audio_url = info['url']
            title = info.get('title', 'Unknown Audio')

        vc.play(discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS))
        await msg.edit(content=f"🎶 **Now Playing:** {title}")

    except Exception as e:
        await ctx.send(f"❌ Error playing audio: {e}")

@bot.command(aliases=['play'])
async def playsound(ctx, url: str):
    await stream_audio(ctx, url)

@bot.command()
async def lofi(ctx):
    # Lofi Girl 24/7 Stream
    await stream_audio(ctx, "https://www.youtube.com/watch?v=jfKfPfyJRdk")

@bot.command()
async def afkbot(ctx):
    # Hardcoded VC ID per your request
    TARGET_VC_ID = 1527215057174532260
    target_channel = bot.get_channel(TARGET_VC_ID)
    
    if not target_channel:
        return await ctx.send("❌ I couldn't find the VC with that ID! Make sure I have permissions to see it.")
    
    await ctx.send("🤖 `Engaging AFK Bot Protocol. Moving to AFK VC...`")
    await stream_audio(ctx, "https://www.youtube.com/watch?v=jfKfPfyJRdk", channel=target_channel)

@bot.command()
async def playlist(ctx, preset: str = None):
    presets = {
        "hype": "https://www.youtube.com/watch?v=aGjtEXUqObI",
        "gaming": "https://www.youtube.com/watch?v=1tGhhz8ExQk",
        "chill": "https://www.youtube.com/watch?v=jfKfPfyJRdk"
    }
    
    if not preset or preset.lower() not in presets:
        options = ", ".join(presets.keys())
        return await ctx.send(f"🎧 Please choose a preset playlist: `{options}`\nExample: `!playlist hype`")
        
    await stream_audio(ctx, presets[preset.lower()])

@bot.command(aliases=['stop', 'dc'])
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Disconnected from the voice channel.")
    else:
        await ctx.send("❌ I'm not in a voice channel right now.")

# ==========================================
# JUMPSQUAD COMMANDS
# ==========================================
@bot.command()
async def jumpsquad(ctx, url: str):
    if not ctx.author.voice:
        return await ctx.send("❌ You need to be in a voice channel first!")
    
    channel = ctx.author.voice.channel
    msg = await ctx.send("🚨 **DEPLOYING THE JUMPSQUAD** 🚨\n`Extracting audio...`")

    # 1. Extract the direct audio stream URL just ONCE for all bots
    try:
        with yt_dlp.YoutubeDL(YTDL_OPTS) as ydl:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
            audio_url = info['url']
            title = info.get('title', 'Unknown Audio')
    except Exception as e:
        return await msg.edit(content=f"❌ Error extracting audio: {e}")

    await msg.edit(content=f"🎶 **Target Locked:** {title}\n`Deploying squad to VC...`")

    # 2. Combine main bot and squad bots into one deployment list
    all_bots = [bot] + squad_bots

    # 3. Connect and play for each bot sequentially
    deployed_count = 0
    for b in all_bots:
        try:
            # The squad bots need to fetch the channel using their own internal cache
            b_channel = b.get_channel(channel.id) or await b.fetch_channel(channel.id)
            
            vc = discord.utils.get(b.voice_clients, guild=b_channel.guild)
            if not vc:
                vc = await b_channel.connect()
            elif vc.channel != b_channel:
                await vc.move_to(b_channel)

            if vc.is_playing():
                vc.stop()

            # Play the shared audio stream
            vc.play(discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS))
            deployed_count += 1
            await asyncio.sleep(0.5) # Prevents Discord from rate-limiting the joins
            
        except Exception as e:
            print(f"Bot {b.user} failed to join/play: {e}")

    await msg.edit(content=f"🔊 **JUMPSQUAD DEPLOYED** 🔊\nNow playing **{title}** on {deployed_count} bots simultaneously!")

@bot.command()
async def squadleave(ctx):
    all_bots = [bot] + squad_bots
    disconnected_count = 0
    
    for b in all_bots:
        vc = discord.utils.get(b.voice_clients, guild=ctx.guild)
        if vc:
            await vc.disconnect()
            disconnected_count += 1
            
    await ctx.send(f"👋 Recalled {disconnected_count} bots from the voice channel.")


# ==========================================
# INTERACTIVE GAMES (UI VIEWS)
# ==========================================

# 1. COINFLIP UI
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

@bot.command()
async def coinflip(ctx, bet: int):
    if bet <= 0 or bet > get_balance(ctx.author.id):
        return await ctx.send("❌ Invalid bet amount! Check your balance.")
    view = CoinflipView(ctx.author, bet)
    await ctx.send(f"🪙 {ctx.author.mention} is betting **{bet} coins**. Choose Heads or Tails!", view=view)


# 2. SLOTS UI
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

@bot.command()
async def slots(ctx, bet: int):
    if bet <= 0 or bet > get_balance(ctx.author.id):
        return await ctx.send("❌ Invalid bet amount! Check your balance.")
    view = SlotsView(ctx.author, bet)
    await ctx.send(f"🎰 {ctx.author.mention} is playing slots for **{bet} coins**!", view=view)


# 3. INTERACTIVE MINES UI
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

@bot.command()
async def mines(ctx, bet: int, bombs: int = 4):
    if bet <= 0 or bet > get_balance(ctx.author.id):
        return await ctx.send("❌ Invalid bet amount! Check your balance.")
    if bombs < 1 or bombs > 15:
        return await ctx.send("❌ You must choose between 1 and 15 bombs.")
    
    view = MinesView(ctx.author, bet, bombs)
    embed = discord.Embed(title=f"🧨 Minefield ({bombs} Bombs)", color=discord.Color.blue())
    embed.description = f"{ctx.author.mention} is playing for **{bet} coins**!\nClick the tiles to find gems 💎 and avoid the bombs 💣."
    await ctx.send(embed=embed, view=view)


# ==========================================
# SERVER KEEP-ALIVE & BOOT
# ==========================================
async def start_all_bots():
    # Grab the squad tokens from Render's environment variables
    squad_tokens = [
        os.environ.get('SQUAD_TOKEN_1'),
        os.environ.get('SQUAD_TOKEN_2'),
        os.environ.get('SQUAD_TOKEN_3'),
        os.environ.get('SQUAD_TOKEN_4')
    ]
    
    # Queue up the main bot
    tasks = [bot.start(os.environ.get('DISCORD_TOKEN'))]
    
    # Queue up the squad bots
    for i, s_bot in enumerate(squad_bots):
        if squad_tokens[i]:
            tasks.append(s_bot.start(squad_tokens[i]))
        else:
            print(f"⚠️ Warning: SQUAD_TOKEN_{i+1} is missing in Render! That bot won't boot.")

    # Run them all concurrently
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    keep_alive()
    # Use asyncio.run to execute the multi-bot startup
    asyncio.run(start_all_bots())
