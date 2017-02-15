import logging
import aiohttp
import asyncio
import math
from aioauth_client import TwitterClient

from opsdroid.connector import Connector
from opsdroid.message import Message


_LOGGER = logging.getLogger(__name__)


class ConnectorTwitter(Connector):

    def __init__(self, config):
        """Setup the connector."""
        logging.debug("Loaded twitter connector")
        super().__init__(config)
        self.name = "twitter"
        self.latest_dm_update = None
        self.config = config
        try:
            self.client = TwitterClient(
                consumer_key=self.config["consumer_key"],
                consumer_secret=self.config["consumer_secret"],
                oauth_token=self.config["oauth_token"],
                oauth_token_secret=self.config["oauth_token_secret"],
            )
        except KeyError as e:
            _LOGGER.error("Missing auth tokens!")

    async def connect(self, opsdroid):
        """Connect to twitter."""
        logging.debug("Connecting to twitter")

    async def listen(self, opsdroid):
        """Listen for new message."""
        while True:
            if self.config.get("enable_dms", True):
                await self._listen_dms(opsdroid)

    async def _listen_dms(self, opsdroid):
        if self.latest_dm_update is not None:
            params = {"since_id": self.latest_dm_update}
        else:
            params = {}
        resp = await self.client.request(
            'GET', 'direct_messages.json', params=params)
        direct_messages = await resp.json()
        resp.release()
        for direct_message in direct_messages:
            _LOGGER.debug(direct_message)
            if self.latest_dm_update is None or self.latest_dm_update < direct_message["id"]:
                self.latest_dm_update = direct_message["id"]
            message = Message(direct_message["text"],
                              direct_message["sender_id"],
                              "dm",
                              self)
            await opsdroid.parse(message)
        await asyncio.sleep(60)  # Requests limited to 15 per 15 min window

    async def respond(self, message):
        """Respond with a message."""
        if message.room == "dm" and self.config.get("enable_dms", True):
            await self._respond_dm(message)

    async def _respond_dm(self, message):
        logging.debug("Responding with: " + message.text)
        params = {"user_id": message.user,
                  "text": message.text}
        resp = await self.client.request(
            'POST', 'direct_messages/new.json', params=params)
        resp.release()
