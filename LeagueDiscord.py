from riotwatcher import LolWatcher,RiotWatcher, ApiError
import discord
from discord.ext import commands
from PIL import Image, ImageDraw
import random
import io 
import numpy as np
from tensorflow.keras.utils import to_categorical
import tensorflow.keras.models

description = '''An example bot to showcase the discord.ext.commands extension
module.
There are a number of utility commands being showcased here.'''

numStats = ["baronKills", "damageDealtToBuildings", "largestKillingSpree", "objectivesStolen", "pentaKills", "quadraKills", "tripleKills", "doubleKills", "timeCCingOthers", "totalDamageDealt", "totalHeal", "totalMinionsKilled", "visionScore", "totalHealsOnTeammates"]
boolStats = ["firstBloodKill", "firstTowerKill"]
challenges = ["abilityUses","acesBefore15Minutes","baronTakedowns","damagePerMinute","dodgeSkillShotsSmallWindow","flawlessAces","getTakedownsInAllLanesEarlyJungleAsLaner","goldPerMinute","maxCsAdvantageOnLaneOpponent","multiKillOneSpell","multiTurretRiftHeraldCount","multikills","saveAllyFromDeath","skillshotsDodged","skillshotsHit","soloBaronKills","soloKills","survivedSingleDigitHpCount","survivedThreeImmobilizesInFight","takedownsBeforeJungleMinionSpawn","teamDamagePercentage","visionScorePerMinute"]

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
token = ''
lol_watcher = LolWatcher('')
api_count = 0

#Calculated the win percentage of a given player
#Fix to either select by queue or find ranked 5x5 or just take all ranked 5s games. 
async def winrateCalc(name: str, region:str):
    player_id = lol_watcher.summoner.by_name(region, name)['id']
    player_info = lol_watcher.league.by_summoner(region, player_id)
    wins = player_info[0]['wins']
    losses = player_info[0]['losses']
    return (wins/(wins+losses)) *100

#Formats discord messages to allow spaces in players names. 
async def formatInfo(info):
    returnInfo = ''
    for x in info:
        returnInfo += x + " "
    return returnInfo.strip()


    
            

def increment_win(sample_dict, key):
    ''' Append multiple values to a key in 
        the given dictionary '''
    try:
        sample_dict[key][0] += 1
    except KeyError:
        sample_dict[key] = [1, 0]
    return sample_dict

def increment_loss(sample_dict, key):
    ''' Append multiple values to a key in 
        the given dictionary '''
    try:
        sample_dict[key][1] += 1
    except KeyError:
        sample_dict[key] = [0, 1]
    return sample_dict

#calculate win percentage from current game 
async def calculateChance(name:str, region:str):
    player_id = lol_watcher.summoner.by_name(region, name)['id']
    details = lol_watcher.spectator.by_summoner(region, player_id)
    match_details = []
    final_percent = 0
    team = ''
    for player in details['participants']:
        match_details.append(player['championId'])
        if player['summonerId'] == player_id:
            team = player['teamId']
    data = [] 
    data.append(match_details)
    model = tensorflow.keras.models.load_model('E:/Projects/LeagueDiscord/test_model')
    predict_data = to_categorical(np.array(data), num_classes=896)
    print("predict_data")
    percentage = model.predict(predict_data)
    if team == 100:
        final_percent = 100 -percentage
    else:
        final_percent = percentage
    return final_percent

#Returns a champion the player often struggles against on a given champion
#Have to make this more efficient. 
async def banCalc(name:str, region:str, champion: str):
    id = lol_watcher.summoner.by_name(region, name)['puuid']
    #api_count += 1
    champion_dict = {}
    difference = 0
    banChamp = ''
    match_history = lol_watcher.match.matchlist_by_puuid(region, id, count=50, queue=420, type='ranked')
    #api_count += 1
    for match in match_history:
        win = ''
        team =''
        enemyPlayers = []
        details = lol_watcher.match.by_id(region,match)
        #api_count += 1
        for player in details['info']['participants']:
            if player['puuid'] == id and player['championName'] == champion:
                win = player['win']
                team = player['teamId']
        for player in details['info']['participants']:
            if player['teamId'] != team:
                #print(player['championName'])
                enemyPlayers.append(player['championName'])
        for player in enemyPlayers:
            if win == True:
                champion_dict = increment_win(champion_dict, player)
            else: 
                champion_dict = increment_loss(champion_dict, player)
    for champion in champion_dict:
        newDifference = champion_dict[champion][1] - champion_dict[champion][0]
        if newDifference > difference:
            difference = newDifference
            banChamp = champion
        elif newDifference == difference:
            if champion_dict[champion][1] + champion_dict[champion][0] > champion_dict[banChamp][1] + champion_dict[banChamp][0]:
                banChamp = champion
    return(banChamp)

async def makeImage(name:str, region:str):
    id = lol_watcher.summoner.by_name(region, name)['puuid']
    champion = ''
    kills = 0
    deaths= 0
    assists=0
    width = 400
    height = 300
    currentHeight = 30
    information = []
    match = lol_watcher.match.matchlist_by_puuid(region, id, count=1, queue=420, type='ranked')[0]
    details = lol_watcher.match.by_id(region,match)
    for player in details['info']['participants']:
            if player['puuid'] == id:
                champion = player['championName']
                kills = player['kills']
                deaths = player['deaths']
                assists = player['assists']
                for data in numStats:
                    if player[data] > 0:
                        information.append(data+' '+ str(player[data]))
                for data in boolStats:
                    if player[data] == True:
                        information.append(data+' '+ str(player[data]))
                for data in challenges:
                    if player['challenges'][data] > 0:
                        information.append(data+' '+ str(player['challenges'][data]))


                #We have info about the player now, create stuff for the image
    #create image here and return back to command. 

    img = Image.new(mode = "RGB", size = (width, height),  color = (255, 255, 255) )
    textFill = ImageDraw.Draw(img)
    textFill.text((10, 10), name, fill=(255,0,0,255))
    textFill.text((10,20), champion, fill=(255,0,0,255))
    textFill.text((340, 10), "K/D/A", fill=(255,0,0,255), align="right")
    textFill.text((340, 20), str(kills)+'/' +str(deaths)+'/' + str(assists), fill=(255,0,0,255), align="right" )
    for x in range(0, 4):
        choice = random.choice(information)
        textFill.text((10, currentHeight), choice, fill=(255,0,0,255))
        currentHeight += 10
    return img


bot = commands.Bot(command_prefix='?', description=description, intents=intents)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

@bot.command()
async def highlight(ctx, *info: str):
    try:
        splitInfo = (await formatInfo(info)).split(",")
        name, region  = splitInfo
    except Exception:
        await ctx.send('Comma between name and region')
        return
    image = await makeImage(name, region )
    with io.BytesIO() as image_binary:
                    image.save(image_binary, 'PNG')
                    image_binary.seek(0)
                    await ctx.send(file=discord.File(fp=image_binary, filename='image.png'))


@bot.command(description='For when you wanna settle the score some other way')
async def ban(ctx, *info: str):
    try:
        splitInfo = (await formatInfo(info)).split(",")
        print(splitInfo)
        name, region, champion = splitInfo
    except Exception:
        await ctx.send('Comma between name and region')
        return
    response = await banCalc(name, region, champion)
    print(api_count)
    await ctx.send("You have lost the most lp to " + response)


@bot.command()
async def winrate(ctx, *info: str):
    try:
        splitInfo = (await formatInfo(info)).split(",")
        name, region = splitInfo
    except Exception:
        await ctx.send('Comma between name and region')
        return
    wr = (await winrateCalc(name, region))
    await ctx.send(wr)

@bot.command()
async def chance(ctx, *info: str):
    splitInfo = (await formatInfo(info)).split(",")
    name, region = splitInfo
    percentage = await calculateChance(name, region)
    print(percentage)
    await ctx.send(percentage)

@bot.command()
async def joined(ctx, member: discord.Member):
    """Says when a member joined."""
    await ctx.send(f'{member.name} joined {discord.utils.format_dt(member.joined_at)}')

bot.run(token)