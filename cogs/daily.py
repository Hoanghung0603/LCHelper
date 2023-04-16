import discord
from discord import app_commands
from discord.ext import tasks, commands
from utils.asset import Assets
from utils.lc_utils import LC_utils
from typing import Optional
import asyncio
import datetime 
from .logging import logging

utc = datetime.timezone.utc
time = datetime.time(hour=22-7, minute=35, tzinfo=utc)

class daily(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.daily.start()

    def cog_unload(self):
        self.daily.cancel()

    @tasks.loop(time = time)
    async def daily(self):
        # Waiting for internal cache, I suppose
        await self.client.wait_until_ready()
        await asyncio.sleep(5)

        guild = await self.client.fetch_guild(1085444549125611530)
        log_channel = await guild.fetch_channel(1091763595777409025)
        await log_channel.send("Daily task started.")
    
        # Fetching daily problem
        daily_challenge_info = LC_utils.get_daily_challenge_info()
        lc_col_daily = self.client.DBClient['LC_db']['LC_daily']
        lc_update = {'$set': {'daily_challenge': daily_challenge_info}}
        lc_col_daily.update_one({'_id': 1}, lc_update)

        # Creating daily thread
        lc_col_tracking = self.client.DBClient['LC_db']['LC_tracking']
        lc_result = lc_col_tracking.find_one({'server_id': 1085444549125611530})

        # This is to prevent this event unintendedly gets triggered multiple times
        if (datetime.datetime.now() - lc_result['last_daily_check']).seconds > 500: 
            guild = await self.client.fetch_guild(1085444549125611530)
            #channel = await guild.fetch_channel(lc_result['daily_thread_channel_id'])
            channel = await guild.fetch_channel(1089769159807733831)
            name = f"{daily_challenge_info['date']}. LeetCode P{daily_challenge_info['id']}"
            await channel.create_thread(name = name, type = discord.ChannelType.public_thread)

        # Checking daily streak of everyone
        lc_col = self.client.DBClient['LC_db']['LC_tmp']
        users = list(lc_col.find())
        for user in users:
            tmp = user
            # This is to prevent this event unintendedly gets triggered multiple times
            if (datetime.datetime.now() - tmp['daily']['last_daily_check']).seconds < 500: continue
            if tmp['daily']['finished_today_daily'] == False:
                tmp['daily']['current_daily_streak'] = 0

            lc_query = {'$set': {
                'daily':{
                    'max_daily_streak': tmp['daily']['max_daily_streak'], 
                    'current_daily_streak': tmp['daily']['current_daily_streak'],
                    'finished_today_daily': False,
                    'last_daily_check': datetime.datetime.now()
                }
            }}
            lc_col.update_one({'discord_id': user['discord_id'], 'daily.last_daily_check': tmp['daily']['last_daily_check']}, lc_query)
            await asyncio.sleep(5)
        await log_channel.send('Daily task completed')

    @daily.error
    async def on_error(self, exception):
        guild = await self.client.fetch_guild(1085444549125611530)
        channel = await guild.fetch_channel(1091763595777409025)
        await channel.send(exception)

    @commands.command()
    @commands.has_permissions(administrator = True)
    async def stop_daily(self, ctx):
        self.daily.stop()
        await ctx.send(f"{Assets.green_tick} **Submission daily task stopped.**")

    @commands.command()
    @commands.has_permissions(administrator = True)
    async def start_daily(self, ctx):
        self.daily.start()
        await ctx.send(f"{Assets.green_tick} **Submission daily task started.**")

    async def complete_daily(self, member: discord.Member):
        lc_col = self.client.DBClient['LC_db']['LC_users']
        lc_user = lc_col.find_one({'discord_id': member.id})
        if lc_user['daily']['finished_today_daily']: 
            return
    
        # Updating streak
        current_streak = lc_user['daily']['current_daily_streak'] + 1
        max_streak = max(lc_user['daily']['max_daily_streak'], current_streak)
        lc_query = {'$set': {
            'daily':{
                'max_daily_streak': max_streak, 
                'current_daily_streak': current_streak,
                'finished_today_daily': True,
                'last_daily_check': lc_user['daily']['last_daily_check']
            }
        }}

        lc_col.update_one({'discord_id': member.id}, lc_query)

        # Updating score
        new_score = lc_user['score'] + 2
        lc_query = {'$set': {
            'score': new_score
        }}
        lc_col.update_one({'discord_id': member.id}, lc_query)
        await logging.on_score_add(logging(self.client), member = member, score = 2, reason = "Daily AC")

async def setup(client):
    #await client.add_cog(daily(client), guilds=[discord.Object(id=1085444549125611530)])
    await client.add_cog(daily(client))
