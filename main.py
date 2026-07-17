import discord
from discord.ext import commands, tasks
import os
import random
from keep_alive import keep_alive

# Sets up the bot with command prefix '!' and enables the required intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 

# We remove the default help command so our custom !cmds looks cleaner
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# --- ECONOMY SYSTEM ---
# A simple dictionary to store user balances. 
user_balances = {}

def get_balance(user_id):
    if user_id not in user_balances:
        user_balances[user_id] = 1000 # Give everyone 1000 starting coins!
    return user_balances[user_id]

def update_balance(user_id, amount):
    user_balances[user_id] = get_balance(user_id) + amount

# --- STATUS SETUP ---
status_list = [
    "touching grass",
    "losing all my coins at !mines",
    "judging your music taste",
    "currently AFK",
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

# --- UTILITY COMMANDS ---
@bot.command()
async def cmds(ctx):
    # A cool embedded menu to list all your bot's features
    embed = discord.Embed(title="🤖 Bot Command Menu", color=discord.Color.blue(), description="Here is everything I can do:")
    embed.add_field(name="🛠️ Utility", value="`!ping` - Check if I'm alive\n`!afk [reason]` - Set your AFK status\n`!bal` - Check your coin balance", inline=False)
    embed.add_field(name="🎲 Games & Casino", value="`!mines [bet]` - Play minesweeper for coins\n`!slots [bet]` - Spin the slot machine\n`!coinflip [bet] [heads/tails]` - Flip a coin for double or nothing", inline=False)
    embed.set_footer(text="Discord friends bot thingy at your service!")
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    await ctx.send('Pong! The bot is online and ready for chaos.')

@bot.command()
async def afk(ctx, *, reason="touching grass"):
    await ctx.send(f'{ctx.author.mention} is now AFK. Reason: {reason}')

@bot.command(aliases=['balance', 'coins'])
async def bal(ctx):
    coins = get_balance(ctx.author.id)
    await ctx.send(f"💰 {ctx.author.mention}, you currently have **{coins} coins**.")

# --- GAMES & ECONOMY ---
@bot.command()
async def coinflip(ctx, bet: int, choice: str):
    choice = choice.lower()
    if choice not in ['heads', 'tails']:
        return await ctx.send("❌ You must choose `heads` or `tails`. Example: `!coinflip 50 heads`")
    
    if bet <= 0 or bet > get_balance(ctx.author.id):
        return await ctx.send("❌ Invalid bet amount! You either don't have enough coins or bet 0.")
    
    outcome = random.choice(['heads', 'tails'])
    if choice == outcome:
        update_balance(ctx.author.id, bet)
        await ctx.send(f"🪙 The coin landed on **{outcome}**! You won **{bet} coins**!")
    else:
        update_balance(ctx.author.id, -bet)
        await ctx.send(f"🪙 The coin landed on **{outcome}**. You lost **{bet} coins**. RIP.")

@bot.command()
async def slots(ctx, bet: int):
    if bet <= 0 or bet > get_balance(ctx.author.id):
        return await ctx.send("❌ Invalid bet amount! Check your balance.")
    
    emojis = ["🍒", "🍋", "🍉", "⭐", "💎"]
    slot1, slot2, slot3 = random.choice(emojis), random.choice(emojis), random.choice(emojis)
    
    result_text = f"🎰 **SLOTS** 🎰\n| {slot1} | {slot2} | {slot3} |\n"
    
    if slot1 == slot2 == slot3:
        winnings = bet * 5
        update_balance(ctx.author.id, winnings)
        await ctx.send(result_text + f"JACKPOT! 🏆 You won **{winnings} coins**!")
    elif slot1 == slot2 or slot2 == slot3 or slot1 == slot3:
        winnings = int(bet * 1.5)
        update_balance(ctx.author.id, winnings)
        await ctx.send(result_text + f"Small win! 🎉 You won **{winnings} coins**.")
    else:
        update_balance(ctx.author.id, -bet)
        await ctx.send(result_text + f"You lost **{bet} coins**. Better luck next time!")

@bot.command()
async def mines(ctx, bet: int = 0):
    if bet > 0 and bet > get_balance(ctx.author.id):
         return await ctx.send("❌ You don't have enough coins for that bet!")
    elif bet < 0:
         return await ctx.send("❌ You can't bet negative coins!")

    # Creates a randomized 5x5 spoiler grid
    grid_size = 5
    safe_emoji = "💎"
    bomb_emoji = "💣"
    grid = ""
    
    bomb_count = 0
    for _ in range(grid_size):
        row = ""
        for _ in range(grid_size):
            # 20% chance for a bomb in each tile
            if random.random() < 0.2:
                row += f"||{bomb_emoji}|| "
                bomb_count += 1
            else:
                row += f"||{safe_emoji}|| "
        grid += row.strip() + "\n"

    # If they placed a bet, the bot "rolls" to see if they survived the minefield
    if bet > 0:
        survival_chance = 0.6  # 60% chance to win the bet
        if random.random() < survival_chance:
            winnings = int(bet * 1.5)
            update_balance(ctx.author.id, winnings)
            result_msg = f"🎉 You navigated the minefield and won **{winnings} coins**!"
        else:
            update_balance(ctx.author.id, -bet)
            result_msg = f"💥 You stepped on a mine and lost your **{bet} coins**!"
    else:
        result_msg = "Just playing for fun! (Tip: use `!mines <bet amount>` to play for coins)"

    embed = discord.Embed(title=f"🧨 {ctx.author.name}'s Minefield", color=discord.Color.red())
    embed.description = f"{result_msg}\n\nClick the tiles at your own risk:\n\n{grid}"
    embed.set_footer(text=f"Total hidden bombs: {bomb_count}")
    
    await ctx.send(embed=embed)

# Starts the web server, then runs the bot using the token from Render
keep_alive()
bot.run(os.environ.get('DISCORD_TOKEN'))
