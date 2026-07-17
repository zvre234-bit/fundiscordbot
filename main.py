import discord
from discord.ext import commands, tasks
import os
import random
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.message_content = True
intents.members = True 

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# ==========================================
# ECONOMY SYSTEM
# ==========================================
user_balances = {}

def get_balance(user_id):
    if user_id not in user_balances:
        user_balances[user_id] = 1000 
    return user_balances[user_id]

def update_balance(user_id, amount):
    user_balances[user_id] = get_balance(user_id) + amount

# ==========================================
# STATUS SETUP
# ==========================================
status_list = [
    "touching grass",
    "robbing your friends",
    "losing my life savings at !slots",
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
# UTILITY & ECONOMY COMMANDS
# ==========================================
@bot.command()
async def cmds(ctx):
    embed = discord.Embed(title="🤖 Bot Command Menu", color=discord.Color.purple())
    embed.add_field(name="🛠️ Utility", value="`!ping` - Check status\n`!afk [reason]` - Set AFK status", inline=False)
    embed.add_field(name="💰 Economy", value="`!bal` - Check your coins\n`!pay [@user] [amount]` - Give coins\n`!rob [@user]` - Try to steal coins\n`!rich` - Server leaderboard", inline=False)
    embed.add_field(name="🎲 Casino", value="`!mines [bet] [bombs]` - Interactive minesweeper\n`!slots [bet]` - Spin the slots\n`!coinflip [bet]` - Double or nothing", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def afk(ctx, *, reason="touching grass"):
    await ctx.send(f'{ctx.author.mention} is now AFK. Reason: {reason}')

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

@bot.command()
async def rob(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        return await ctx.send("❌ You can't rob yourself!")
    if get_balance(member.id) < 50:
        return await ctx.send("❌ They are too poor to rob right now.")
    if get_balance(ctx.author.id) < 50:
        return await ctx.send("❌ You need at least 50 coins to cover the fine if you get caught!")

    # 40% chance to succeed
    if random.random() < 0.40:
        steal_amount = random.randint(10, int(get_balance(member.id) * 0.3)) # Steal up to 30% of their cash
        update_balance(member.id, -steal_amount)
        update_balance(ctx.author.id, steal_amount)
        await ctx.send(f"🥷 **SUCCESS!** {ctx.author.mention} snuck away with **{steal_amount} coins** from {member.mention}!")
    else:
        fine = 50
        update_balance(ctx.author.id, -fine)
        update_balance(member.id, fine)
        await ctx.send(f"🚨 **BUSTED!** {ctx.author.mention} got caught trying to rob {member.mention} and had to pay a **{fine} coin** fine!")

@bot.command(aliases=['leaderboard', 'top'])
async def rich(ctx):
    # Sorts the dictionary by balances in descending order
    sorted_balances = sorted(user_balances.items(), key=lambda item: item[1], reverse=True)
    
    embed = discord.Embed(title="🏆 Richest Players", color=discord.Color.gold())
    board = ""
    for index, (user_id, balance) in enumerate(sorted_balances[:5]):
        user = bot.get_user(user_id)
        username = user.name if user else f"Unknown User ({user_id})"
        board += f"**{index + 1}.** {username} - 💰 {balance}\n"
    
    embed.description = board if board else "Nobody has any money yet!"
    await ctx.send(embed=embed)

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
            # Hit a bomb! You lose your original bet.
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
            # Safe tile!
            self.style = discord.ButtonStyle.success
            self.emoji = "💎"
            self.label = ""
            self.disabled = True
            view.safe_clicks += 1
            
            # The more bombs on the board, the faster the multiplier grows!
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
        
        # Creates a 4x4 grid (16 tiles) based on your custom bomb count
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
            
        # Give them their profit (current winnings minus original bet, since they haven't been charged the bet yet)
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


# Starts the web server, then runs the bot
keep_alive()
bot.run(os.environ.get('DISCORD_TOKEN'))
