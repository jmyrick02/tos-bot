import discord, datetime, asyncio, gspread # TODO a death system
from discord.ext import tasks, commands  # TODO an automatic voting system
from oauth2client.service_account import ServiceAccountCredentials # TODO add an option for random assignment of roles from a role list. eg. you put Random as the role name when adding the player and then when the game starts it uses the supplied (optional) role list to randomly assign roles to players, taking into account which roles were manually assigned
from enum import Enum  # TODO add system for custom roles

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
sheets_client = gspread.authorize(creds)
sheet = sheets_client.open('ToS Bot Data').sheet1

bot = commands.Bot(command_prefix='ts!')
games = {}

@tasks.loop(seconds=60)
async def update():
    time = datetime.datetime.utcnow()

    for guild_id in games:
        game = games[guild_id]
        if (game.in_progress and (time.hour == game.transition_times[0][0] and time.minute == game.transition_times[0][1]) or (time.hour == game.transition_times[1][0] and time.minute == game.transition_times[1][1])):
            await game.progress_time()

class SalemRole(Enum):
    INVESTIGATOR = 1
    LOOKOUT = 2
    PSYCHIC = 3
    SHERIFF = 4
    SPY = 5
    TRACKER = 6
    BODYGUARD = 7
    CRUSADER = 8
    DOCTOR = 9
    ESCORT = 10
    MAYOR = 11
    MEDIUM = 12
    TRANSPORTER = 13
    JAILOR = 14
    VETERAN = 15
    VIGILANTE = 16
    AMBUSHER = 17
    GODFATHER = 18
    MAFIOSO = 19
    BLACKMAILER = 20
    CONSIGLIERE = 21
    CONSORT = 22
    FRAMER = 23
    HYPNOTIST = 24
    JANITOR = 25
    EXECUTIONER = 26
    JESTER = 27
    WITCH = 28
    AMNESIAC = 29
    GUARDIAN_ANGEL = 30
    SURVIVOR = 31
    ARSONIST = 32
    JUGGERNAUT = 33
    PIRATE = 34
    SERIAL_KILLER = 35
    WEREWOLF = 36
    CUSTOM = 37

class Player:
    """The class for players"""

    def __init__(self, user_id, personal_channel_id, role):
        self.user_id = user_id
        self.personal_channel_id = personal_channel_id
        self.role = role
        self.alive = True

class Game:
    """The main game class"""

    def __init__(self, bot, guild_id, in_progress, game_channel_id, player_role_id, transition_times, players):
        self.day = .5  # 1 = day 1, 1.5 = night 1 etc.
        self.bot = bot
        self.game_channel_id = game_channel_id
        self.guild_id = guild_id
        self.player_role_id = player_role_id
        self.transition_times = transition_times
        self.players = players
        self.in_progress = in_progress

    async def progress_time(self):
        self.day += 0.5
        if int(self.day) == self.day:  # day time
            await self.bot.get_channel(self.game_channel_id).send(f'**DAY {int(self.day)}**')
            await self.bot.get_channel(self.game_channel_id).set_permissions(self.bot.get_guild(self.guild_id).get_role(self.player_role_id), send_messages=True)
        else:
            await self.bot.get_channel(self.game_channel_id).send(f'**NIGHT {int(self.day)}**')
            if (self.day - 0.5) % 2 == 0:
                await self.bot.get_channel(self.game_channel_id).send(f'**There is a full moon out tonight.**')
                for werewolf in self.players_from_role(SalemRole.WEREWOLF):
                    await self.bot.get_channel(werewolf.personal_channel_id).send(f'{self.bot.get_user(werewolf.user_id).mention} **There is a full moon out tonight.**')
            await self.bot.get_channel(self.game_channel_id).send(f'{self.bot.get_guild(self.guild_id).get_role(self.player_role_id).mention} Remember to use your roles tonight.')
            await self.bot.get_channel(self.game_channel_id).set_permissions(self.bot.get_guild(self.guild_id).get_role(self.player_role_id), send_messages=False)
        save(self.guild_id)

    def player_from_id(self, user_id):
        for player in self.players:
            if user_id == player.user_id:
                return player

    def players_from_role(self, role):
        players = []
        for player in self.players:
            if player.alive and player.role == role:
                players.append(player)
        return players

@bot.event
async def on_ready():
    print('Logged on as', bot.user)

    update.start()
    for guild in bot.guilds:
        load(guild.id)

@bot.command(brief='Sets up a game instance')
@commands.has_permissions(administrator=True)
async def setup_game(ctx, player_role: discord.Role, hour1: int, minute1: int, hour2: int, minute2: int):
    if not ctx.guild.id in games:
        guild_id = ctx.guild.id
        game_channel_id = ctx.channel.id
        player_role_id = player_role.id
        transition_times = [[hour1, minute1], [hour2, minute2]]
        games[guild_id] = Game(
            bot, guild_id, False, game_channel_id, player_role_id, transition_times, [])
        save(guild_id)

        await ctx.send('The game instance is set up. Use the command "delete_game" to delete this game instance and to be able to restart. Finish set up using the command "add_player" in each player\'s respective personal channel. Use the command "game_info" to review info about this instance. Use the command "start_game" to begin this instance.')
    else:
        await ctx.send('A game instance already exists. Delete this instance with the command "delete_game" to be able to create a new one.')
    await ctx.message.delete()

@bot.command(brief='Adds a player and their role to the game instance.', description='List of roles (ignore the numbers): https://drive.google.com/file/d/1MdQJCUaKRM_jPIPN2NU3IcY0Vtp2fnI3/view?usp=sharing')
@commands.has_permissions(administrator=True)
async def add_player(ctx, nick: str, role):
    game = games[ctx.guild.id]
    try:
        players = [user for user in ctx.guild.members if nick == user.display_name or nick == str(user.id) or nick == user.name or nick == str(user)]

        if len(players) == 1:
            player = players[0]
        else:
            player = None
            await ctx.send('There are multiple matches for the entered nickname. Please redo this command with their full discord name.')

        game.players.append(Player(player.id, ctx.channel.id, SalemRole[role.upper()]))
        save(ctx.guild.id)
        await ctx.channel.set_permissions(player, read_messages=True, send_messages=True, manage_messages=True, read_message_history=True)
        await ctx.send(f'{player.mention} Welcome! This is your own private channel. This is where you are told what your role is, and where you tell the host how you use it as well. On top of that, this is where you store your will. You must have it pinned, or it will not go through, in the case that you die. You have been given pin perms for this channel.')
        await ctx.message.delete()
    except:
        await ctx.send(f'Role or user does not exist. To use a custom role, put CUSTOM for the role parameter. See list of roles here: https://drive.google.com/file/d/1MdQJCUaKRM_jPIPN2NU3IcY0Vtp2fnI3/view?usp=sharing')

@bot.command(brief='Starts the game instance')
@commands.has_permissions(administrator=True)
async def start_game(ctx):
    games[ctx.guild.id].in_progress = True
    await games[ctx.guild.id].progress_time()

    for player in games[ctx.guild.id].players:
        await bot.get_channel(player.personal_channel_id).send(f'{bot.get_user(player.user_id).mention}\nYou are the **{player.role.name}**. The game has begun in {bot.get_channel(games[ctx.guild.id].game_channel_id).mention}')
        if player.role == SalemRole.CUSTOM:
            await bot.get_channel(player.personal_channel_id).send('Your role is a custom role. The host will give the role to you.')
    await ctx.message.delete()

@bot.command(aliases=['utc'], brief='Gives the current time in UTC')
async def time(ctx):
    await ctx.send(f'The time is {str(datetime.datetime.utcnow().time())[:5]} UTC')

@bot.command(brief='Changes the transition times for the game instance')
@commands.has_permissions(administrator=True)
async def set_transition_times(ctx, hour1, minute1, hour2, minute2):
    games[ctx.guild.id].transition_times = [
        [int(hour1), int(minute1)], [int(hour2), int(minute2)]]
    save(ctx.guild.id)
    await ctx.message.add_reaction('✅')

@bot.command(brief='Sets a players role to a new role')
@commands.has_permissions(administrator=True)
async def set_role(ctx, nick, role):
    game = games[ctx.guild.id]

    players = [member for member in ctx.guild.members if nick == member.display_name or nick == str(member.id) or nick == member.name or nick == str(member)]

    if len(players) == 1:
        user = players[0]
    else:
        user = None
        await ctx.send('There are multiple matches for the entered nickname. Please redo this command with their full discord name or id.')

    player = game.player_from_id(user.id)
    player.role = SalemRole[role]
    save(ctx.guild.id)
    await bot.get_channel(player.personal_channel_id).send(f'{user.mention} Your role has been changed to {player.role.name}')

    await ctx.message.add_reaction('✅')

@bot.command(aliases=['w', 'message', 'msg', 'pm', 'dm'], brief='Whispers to a player in the game and tells everyone in the game')
async def whisper(ctx, nick, *, message):
    recipient = discord.utils.get(ctx.guild.members, display_name=nick)

    players = [member for member in ctx.guild.members if nick == member.display_name or nick == str(member.id) or nick == member.name or nick == str(member)]

    if len(players) == 1:
        recipient = players[0]
    else:
        recipient = None
        await ctx.send('There are multiple matches for the entered nickname. Please redo this command with their full discord name or id.')

    if ctx.guild.id in games and games[ctx.guild.id].day == int(games[ctx.guild.id].day) and recipient != ctx.author:
        await bot.get_channel(games[ctx.guild.id].player_from_id(recipient.id).personal_channel_id).send(f'**{ctx.author.display_name}** whispers *{message}*')
        await bot.get_channel(games[ctx.guild.id].game_channel_id).send(f'**{ctx.author.display_name}** is whispering to **{recipient.display_name}**')

        for blackmailer in games[ctx.guild.id].players_from_role(SalemRole.BLACKMAILER):
            await bot.get_channel(blackmailer.personal_channel_id).send(f'**{ctx.author.display_name}** whispers *{message}* to **{recipient.display_name}**')

        await ctx.message.add_reaction('✅')

@bot.command(aliases=['player_list', 'players_list', 'plist'], brief='Lists all players in the game.')
async def list_players(ctx):
    game = games[ctx.guild.id]
    await ctx.send(f'**Players:**')
    for player in game.players:
        await ctx.send(f'•{ctx.guild.get_member(player.user_id).display_name} ({bot.get_user(player.user_id)})')

@bot.command(aliases=['ginfo', 'game_data', 'gdata', 'data'], brief='Lists info about the game')
@commands.has_permissions(administrator=True)
async def game_info(ctx):
    if ctx.guild.id in games:
        game = games[ctx.guild.id]
        await ctx.send(f'**In Progress:** {game.in_progress}\n**Game Channel ID:** {game.game_channel_id}\n**Player Role ID:** {game.player_role_id}\n**Transition Times:** {game.transition_times}\n**Current Day:** {game.day}\n**Players:**')
        for player in game.players:
            await ctx.send(f'•{ctx.guild.get_member(player.user_id).display_name} - {player.role.name}')
    else:
        await ctx.send('There is no game instance. Use the command "setup_game" to create one.')

def save(guild_id):
    game = games[guild_id]
    data = [str(guild_id), str(game.in_progress), str(game.game_channel_id), str(game.player_role_id), str(game.transition_times[0][0]), str(
        game.transition_times[0][1]), str(game.transition_times[1][0]), str(game.transition_times[1][1]), str(game.day)]

    for player in game.players:
        data.append(str(player.user_id))
        data.append(str(player.personal_channel_id))
        data.append(str(player.role.name))

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

        in_progress = bool(data[1])
        game_channel_id = int(data[2])
        player_role_id = int(data[3])
        transition_times = [[int(data[4]), int(data[5])], [
            int(data[6]), int(data[7])]]
        day = float(data[8])

        players = []
        for i in range(9, len(data) - 1, 3):
            user_id = int(data[i])
            personal_channel_id = int(data[i + 1])
            role_name = data[i + 2]
            players.append(Player(user_id, personal_channel_id, SalemRole[role_name]))

        games[guild_id] = Game(bot, guild_id, in_progress, game_channel_id, player_role_id, transition_times, players)
        games[guild_id].day = day
        print('Loaded game of guild_id:', guild_id)
    except:
        print(f'Data for {guild_id} does not exist. Game instance not created.')

@bot.command(brief='Progress time manually. Only use if necessary.')
@commands.has_permissions(administrator=True)
async def progress_time(ctx):
    if ctx.guild.id in games:
        await games[ctx.guild.id].progress_time()
        await ctx.message.add_reaction('✅')
    else:
        await ctx.send('There is no game instance. Use the command "setup_game" to create one.')

@bot.command(brief='Deletes the current game instance.')
@commands.has_permissions(administrator=True)
async def delete_game(ctx):
    if ctx.guild.id in games:
        for player in games[ctx.guild.id].players:
            pinned_messages = await bot.get_channel(player.personal_channel_id).pins()
            for pin in pinned_messages:
                await pin.unpin()

        del games[ctx.guild.id]

        guild_ids = sheet.col_values(1)
        row = guild_ids.index(str(ctx.guild.id)) + 1
        sheet.delete_rows(row)

        await ctx.message.add_reaction('✅')
    else:
        await ctx.send('There is no game instance. Use the command "setup_game" to create one.')

bot.run('NzE5NTUzNDM3OTMwNjE4OTQy.Xt5IMg.wUU2ERW_9UMdqbsmWKVsO6yEHis')
