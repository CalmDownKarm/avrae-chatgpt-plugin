import os
import json
import quart
import discord
import asyncio
import quart_cors
import nest_asyncio
from discord.ext import commands
from quart import Quart, request
from dataclasses import dataclass
from quart_schema import QuartSchema, validate_request, validate_response

with open("keys.json") as f:
    keys = json.load(f)
TOKEN = keys["DISCORD TOKEN"]
# Hardcoded User ID for Avrae
AVRAE_BOT_USER = "Avrae#6944"
SERVERID = 1103012947376226466
CHANNELID = 1103012948022145067


nest_asyncio.apply()
app = quart_cors.cors(quart.Quart(__name__), allow_origin="https://chat.openai.com")
QuartSchema(app)

# Dataclasses - mostly only needed to auto-generate OpenAPI spec
@dataclass
class Message:
    message: str

@dataclass
class State:
    messages: list[dict[str, str]]


intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@app.before_serving
async def before_serving():
    loop = asyncio.get_event_loop()
    await client.login(TOKEN)
    loop.create_task(client.connect())

@app.route("/")
async def hello():
    return "Hello World!"

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    server = client.get_guild(SERVERID)
    channel = server.get_channel(CHANNELID)
    if message.content.startswith('$hello'):
        await channel.send("I attack [[2d10]] to hit")

def format_message(message):
    dict_ = {key: str(getattr(message, key)) for key in ["content", "author"]}
    dict_["embed"] = ""
    for embed in message.embeds:
        dict_["embed"] += str(embed.to_dict())

    return dict_

@app.route("/get_state")
@validate_response(State)
async def get_state():
    server = client.get_guild(SERVERID)
    channel = server.get_channel()
    messages = [message async for message in channel.history(limit=5000)]
    messages = [format_message(message) for message in messages if str(message.author) == AVRAE_BOT_USER]
    return State(messages=messages)


@app.route("/post_message", methods=["POST"])
@validate_request(Message)
@validate_response(Message)
async def post_message(data: Message):
    # data = await request.get_json()
    server = client.get_guild(SERVERID)
    channel = server.get_channel(CHANNELID)
    await channel.send(data.message)
    return Message(message="Message sent!")

@client.event
async def on_ready():
    print("Initiated!")


@app.get("/logo.png")
async def plugin_logo():
    filename = 'logo.png'
    return await quart.send_file(filename, mimetype='image/png')

@app.get("/.well-known/ai-plugin.json")
async def plugin_manifest():
    host = request.headers['Host']
    with open("ai-plugin.json") as f:
        text = f.read()
        # This is a trick we do to populate the PLUGIN_HOSTNAME constant in the manifest
        text = text.replace("PLUGIN_HOSTNAME", f"http://{host}")
        return quart.Response(text, mimetype="text/json")
    
@app.get("/openapi.yaml")
async def openapi_spec():
    host = request.headers['Host']
    with open("openapi.yaml") as f:
        text = f.read()
        # This is a trick we do to populate the PLUGIN_HOSTNAME constant in the OpenAPI spec
        text = text.replace("PLUGIN_HOSTNAME", f"http://{host}")
        return quart.Response(text, mimetype="text/yaml")

app.run()