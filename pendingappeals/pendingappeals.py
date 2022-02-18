import asyncio
import aiohttp
import discord
from redbot.core import commands, Config, checks
import discord.errors
from redbot.core.bot import Red
from typing import *
import logging
import datetime
from bs4 import BeautifulSoup
import itertools
from redbot.core.utils.chat_formatting import pagify

BASE_URL = "https://forum.ss13.co/"


class PendingAppeals(commands.Cog):
    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, 95222448842)
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        asyncio.create_task(self.session.cancel())

    async def test_thread(self, elem, labels_only=True):
        try:
            if "forumdisplay_sticky" in elem.find_parent("td").get_attribute_list(
                "class"
            ):
                return None
            if "label" in elem.previousSibling.previousSibling.get_attribute_list(
                "class"
            ):
                return None
        except:
            pass
        url = BASE_URL + elem.a.get_attribute_list("href")[0]
        if not labels_only:
            async with self.session.get(url) as res:
                bs = BeautifulSoup(await res.text(), "html")
                for auth_info in bs.find_all(class_="author_information"):
                    try:
                        rank = auth_info.find(class_="smalltext").text.strip().lower()
                        if "admin" in rank or "developer" in rank:
                            return None
                    except:
                        pass
        return f"<{url}> {elem.a.text}"

    async def scrape_page(self, page, forum_id, labels_only=True):
        result = []
        async with self.session.get(
            BASE_URL + f"forumdisplay.php?fid={forum_id}&page={page}"
        ) as res:
            bs = BeautifulSoup(await res.text())
            elems = bs.find_all(class_="subject_new")
            result = await asyncio.gather(
                *[self.test_thread(elem, labels_only) for elem in elems]
            )
        return [x for x in result if x is not None]

    @commands.command()
    @checks.admin()
    async def pendingappeals(
        self, ctx: commands.Context, pages: int = 4, check_only_labels: bool = True
    ):
        """Scrapes the Goonstation forum for unresponded to appeals."""
        results = await asyncio.gather(
            *(
                [
                    self.scrape_page(page, forum_id=4, labels_only=check_only_labels)
                    for page in range(1, pages + 1)
                ]
                + [
                    self.scrape_page(page, forum_id=35, labels_only=False)
                    for page in range(1, pages + 1)
                ]
            )
        )
        result = itertools.chain(*results)
        if not result:
            await ctx.send("No pending appeals found")
        else:
            for page in pagify("\n".join(result)):
                await ctx.send(page)
