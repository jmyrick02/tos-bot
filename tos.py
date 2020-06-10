import discord, datetime, asyncio, os, gspread # TODO make it work on more than one server at once, remove os dependency
from discord.ext import tasks, commands # TODO add a player registration system for a voting system and personal channel assignment
from oauth2client.service_account import ServiceAccountCredentials # TODO make one server able to host multiple games at once

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
sheets_client = gspread.authorize(creds)
sheet = sheets_client.open('ToS Bot Data').sheet1

bot = commands.Bot(command_prefix='ts!')
games = {}

@tasks.loop(seconds=.1)
async def update():
    time = datetime.datetime.utcnow()

    for guild_id in games:
        game = games[guild_id]
        if (time.hour == game.transition_times[0][0] and time.minute == game.transition_times[0][1]) or (time.hour == game.transition_times[1][0] and time.minute == game.transition_times[1][1]):
            await game.progress_time()
            await asyncio.sleep(60)

class Game:
    """The main game class"""
    def __init__(self, bot, guild_id, game_channel_id, player_role_id, transition_times):
        self.day = 1 # 1 = day 1, 1.5 = night 1 etc.
        self.bot = bot
        self.game_channel_id = game_channel_id
        self.guild_id = guild_id
        self.player_role_id = player_role_id
        self.transition_times = transition_times

    async def progress_time(self):
        self.day += 0.5
        if int(self.day) == self.day: # day time
            await self.bot.get_channel(self.game_channel_id).send(f'**DAY {int(self.day)}**')
            await self.bot.get_channel(self.game_channel_id).set_permissions(self.bot.get_guild(self.guild_id).get_role(self.player_role_id), send_messages=True)
        else:
            await self.bot.get_channel(self.game_channel_id).send(f'**NIGHT {int(self.day)}**')
            await self.bot.get_channel(self.game_channel_id).send(f'{self.bot.get_guild(self.guild_id).get_role(self.player_role_id).mention} Remember to use your roles tonight.')
            await self.bot.get_channel(self.game_channel_id).set_permissions(self.bot.get_guild(self.guild_id).get_role(self.player_role_id), send_messages=False)
        save(self.guild_id)

@bot.event
async def on_ready():
    print('Logged on as', bot.user)
    
    update.start()
    for guild in bot.guilds:
        load(guild.id)

@bot.command(brief='Starts a game instance')
@commands.has_permissions(administrator=True)
async def start_game(ctx, player_role: discord.Role, hour1: int, minute1: int, hour2: int, minute2: int):
    if not ctx.guild.id in games:
        guild_id = ctx.guild.id
        game_channel_id = ctx.channel.id
        player_role_id = player_role.id
        transition_times = [[hour1, minute1], [hour2, minute2]]
        games[guild_id] = Game(bot, guild_id, game_channel_id, player_role_id, transition_times)
    
        await ctx.send('The game instance is set up. Use the command "delete_game" to delete this game instance and to be able to restart.')
        await games[ctx.guild.id].progress_time()
    else:
       await ctx.send('A game instance already exists. Delete this instance with the command "delete_game" to be able to create a new one.') 

@bot.command(aliases=['utc'], brief='Gives the current time in UTC')
async def time(ctx):
    await ctx.send(f'The time is {str(datetime.datetime.utcnow().time())[:5]} UTC')

@bot.command(aliases=['w', 'message', 'msg', 'pm', 'dm'], brief='Whispers to a specified channel and tells everyone in the game')
async def whisper(ctx, channel: discord.TextChannel, *, message):
    if ctx.guild.id in games:
        await channel.send(f'*{ctx.author.display_name} whispers {message}*')
        await bot.get_channel(games[ctx.guild.id].game_channel_id).send(f'**{ctx.author.display_name}** is whispering to **{channel}**')
        print(f'{ctx.author.display_name} whispers {message} to {channel}')

@bot.command(aliases=['ginfo', 'game_data', 'gdata', 'data'], brief='Lists info about the game')
@commands.has_permissions(administrator=True)
async def game_info(ctx):
    if ctx.guild.id in games:
        game = games[ctx.guild.id]
        await ctx.send(f'**Game Channel ID:** {game.game_channel_id}\n**Player Role ID:** {game.player_role_id}\n**Transition Times:** {game.transition_times}\n**Current Day:** {game.day}')
    else:
        await ctx.send('There is no game instance. Use the command "start_game" to create one.')

def save(guild_id):
    game = games[guild_id]
    data = [str(guild_id), str(game.game_channel_id), str(game.player_role_id), str(game.transition_times[0][0]), game.transition_times[0][1], game.transition_times[1][0], game.transition_times[1][1], game.day]

    guild_ids = sheet.col_values(1)
    row = len(guild_ids) + 1
    if str(guild_id) in guild_ids:
        row = guild_ids.index(str(guild_id)) + 1
        sheet.delete_rows(row)
 
    sheet.insert_row(data, row)

def load(guild_id):
    data = sheet.col_values(1)
    
    guild_ids = sheet.col_values(1)
    try:
        row = guild_ids.index(str(guild_id)) + 1
        data = sheet.row_values(row)

        game_channel_id = int(data[1])
        player_role_id = int(data[2])
        transition_times = [[int(data[3]), int(data[4])], [int(data[5]), int(data[6])]]
        day = float(data[7])
        games[guild_id] = Game(bot, guild_id, game_channel_id, player_role_id, transition_times)
        games[guild_id].day = day
        print('Loaded game of guild_id:', guild_id)
    except:
        print(f'Data for {guild_id} does not exist. Game instance not created.')
    
@bot.command(brief='Progress time manually. Only use if necessary.')
@commands.has_permissions(administrator=True)
async def progress_time(ctx):
    if ctx.guild.id in games:
        await games[ctx.guild.id].progress_time()
    else:
        await ctx.send('There is no game instance. Use the command "start_game" to create one.')

@bot.command(brief='Deletes the current game instance.')
@commands.has_permissions(administrator=True)
async def delete_game(ctx):
    if ctx.guild.id in games:
        del games[ctx.guild.id]
        
        guild_ids = sheet.col_values(1)
        row = guild_ids.index(str(ctx.guild.id)) + 1
        sheet.delete_rows(row)

        await ctx.send('Game instance deleted.')
    else:
        await ctx.send('There is no game instance. Use the command "start_game" to create one.')

bot.run('NzE5NTUzNDM3OTMwNjE4OTQy.Xt5IMg.wUU2ERW_9UMdqbsmWKVsO6yEHis')
