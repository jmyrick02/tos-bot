import discord, datetime, asyncio, os
from discord.ext import tasks, commands

bot = commands.Bot(command_prefix='ts!')
game = None

class Game:
    """The main game class"""
    def __init__(self, bot, guild_id, game_channel_id, player_role_id, transition_times):
        self.day = 1 # 1 = day 1, 1.5 = night 1 etc.
        self.bot = bot
        self.game_channel_id = game_channel_id
        self.guild_id = guild_id
        self.player_role_id = player_role_id
        self.transition_times = transition_times
        self.update.start()

    @tasks.loop(seconds=.1)
    async def update(self):
        time = datetime.datetime.utcnow()
        if (time.hour == self.transition_times[0][0] and time.minute == self.transition_times[0][1]) or (time.hour == self.transition_times[1][0] and time.minute == self.transition_times[1][1]):
            await self.progress_time()
            await asyncio.sleep(60)

    async def progress_time(self):
        self.day += 0.5
        if int(self.day) == self.day: # day time
            await self.bot.get_channel(self.game_channel_id).send(f'**DAY {int(self.day)}**')
            await self.bot.get_channel(self.game_channel_id).set_permissions(self.bot.get_guild(self.guild_id).get_role(self.player_role_id), send_messages=True)
        else:
            await self.bot.get_channel(self.game_channel_id).send(f'**NIGHT {int(self.day)}**')
            await self.bot.get_channel(self.game_channel_id).send(f'{self.bot.get_guild(self.guild_id).get_role(self.player_role_id).mention} Remember to use your roles tonight.')
            await self.bot.get_channel(self.game_channel_id).set_permissions(self.bot.get_guild(self.guild_id).get_role(self.player_role_id), send_messages=False)
        await save(None)

@bot.event
async def on_ready():
    print('Logged on as', bot.user)
    await load(None)

@bot.command(brief='Starts a game instance')
@commands.has_permissions(administrator=True)
async def start_game(ctx, player_role: discord.Role, hour1: int, minute1: int, hour2: int, minute2: int):
    global game
    if game is None:
        guild_id = ctx.guild.id
        game_channel_id = ctx.channel.id
        player_role_id = player_role.id
        transition_times = [[hour1, minute1], [hour2, minute2]]
        game = Game(bot, guild_id, game_channel_id, player_role_id, transition_times)
    
        await ctx.send('The game instance is set up. Use the command "delete_game" to delete this game instance and be able to restart.')
        await game.progress_time()
    else:
       await ctx.send('A game instance already exists. Delete this with the command "delete_game" to create a new one.') 

@bot.command(aliases=['utc'], brief='Gives the current time in UTC')
async def time(ctx):
    await ctx.send(f'The time is {str(datetime.datetime.utcnow().time())[:5]} UTC')

@bot.command(aliases=['w', 'message', 'msg', 'pm', 'dm'], brief='Whispers to a specified channel and tells everyone in the game')
async def whisper(ctx, channel: discord.TextChannel, *, message):
    if game is not None:
        await channel.send(f'*{ctx.author.display_name} whispers {message}*')
        await bot.get_channel(game.game_channel_id).send(f'**{ctx.author.display_name}** is whispering to **{channel}**')

@bot.command(aliases=['ginfo', 'game_data', 'gdata', 'data'], brief='Lists info about the game')
@commands.has_permissions(administrator=True)
async def game_info(ctx):
    if game is not None:
        await ctx.send(f'**Guild ID:** {game.guild_id}\n**Game Channel ID:** {game.game_channel_id}\n**Player Role ID:** {game.player_role_id}\n**Transition Times:** {game.transition_times}\n**Current Day:** {game.day}')
    else:
        await ctx.send('There is no game instance. Use the command "start_game" to create one.')

@bot.command(brief='Saves the game data manually. Only use if necessary.')
@commands.has_permissions(administrator=True)
async def save(ctx):
    if game is not None:
        file = open('data', 'w')
        file.write(str(game.guild_id) + '\n')
        file.write(str(game.game_channel_id) + '\n')
        file.write(str(game.player_role_id) + '\n')
        file.write(f'{game.transition_times[0][0]} {game.transition_times[0][1]} {game.transition_times[1][0]} {game.transition_times[1][1]}\n')
        file.write(str(game.day))

@bot.command(brief='Loads the game data manually. Only use if necessary.')
@commands.has_permissions(administrator=True)
async def load(ctx):
    global game
    try:
        file = open('data', 'r')
        guild_id = int(file.readline())
        game_channel_id = int(file.readline())
        player_role_id = int(file.readline())
        transition_strings = file.readline()[:-1].split()
        transition_times = [[int(transition_strings[0]), int(transition_strings[1])], [int(transition_strings[2]), int(transition_strings[3])]]
        day = float(file.readline())
        game = Game(bot, guild_id, game_channel_id, player_role_id, transition_times)
        game.day = day
        print('Loaded game of guild_id:', guild_id)
    except:
        game = None
        print('Data file does not exist. Game instance not created.')
    
@bot.command(brief='Progress time manually. Only use if necessary.')
@commands.has_permissions(administrator=True)
async def progress_time(ctx):
    if game is not None:
        await game.progress_time()

@bot.command(brief='Deletes the current game instance.')
@commands.has_permissions(administrator=True)
async def delete_game(ctx):
    global game
    if game is not None:
        game.update.cancel()
        del game
        game = None
        os.remove('data')
        await ctx.send('Game instance deleted.')
    else:
        await ctx.send('There is no game instance. Use the command "start_game" to create one.')

bot.run('NzE5NTUzNDM3OTMwNjE4OTQy.Xt5IMg.wUU2ERW_9UMdqbsmWKVsO6yEHis')            