from quart import Quart, render_template, redirect, url_for, request
from quart_discord import DiscordOAuth2Session
from quart_discord.models.user import User
import os
from dotenv import load_dotenv
from db import MotorDB
import aiohttp
from functools import wraps
from bson.objectid import ObjectId

load_dotenv()

motor_db = MotorDB().motor_client["dashboard"]

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = (
    "1"  # this is required because OAuth 2 utilizes https.
)

app = Quart(__name__)

app.config["SECRET_KEY"] = os.getenv("QUART_SECRET_KEY")

app.config["DISCORD_CLIENT_ID"] = os.getenv("DISCORD_CLIENT_ID")  # Discord client ID.
app.config["DISCORD_CLIENT_SECRET"] = os.getenv(
    "DISCORD_CLIENT_SECRET"
)  # Discord client secret.
app.config["DISCORD_REDIRECT_URI"] = (
    f"http://{os.getenv('SERVER_IP')}:8082/callback"  # URL to your callback endpoint.
)

discord = DiscordOAuth2Session(app)  # handle session for authentication

allowed = [396892407884546058, 1200519236834041898, 425661467904180224]
# allowed = [1200519236834041898, 425661467904180224]

async def verify(mode: str):
    """Returns User or a redirect thing"""
    try:
        user = await discord.fetch_user()  # fetch data for user
    except:
        if mode == "GET":
            return redirect(
                url_for("login")
            )
        elif mode == "POST":
            return "You need to login first", 401
            
    if user.id not in allowed:
        if mode == "GET":
            return await render_template("forbidden.html", user=user)
        elif mode == "POST":
            return "You are not in the list", 401    
            
    return user

def auth_required(method="GET"):  # Accept "GET" or "POST"
    def decorator(endpoint_func):
        @wraps(endpoint_func)
        async def wrapper(*args, **kwargs):
            user = await verify(method)  # Use the provided method
            if not isinstance(user, User):
                return user  # Return error response if authentication fails
            return await endpoint_func(user, *args, **kwargs)  # Pass user object to route

        return wrapper
    return decorator  # Return the actual decorator


@app.route("/")
async def home():
    return await render_template("home.html", authorized=await discord.authorized)


@app.route("/login")
async def login():
    return await discord.create_session()  # handles session creation for authentication


@app.route("/callback")
async def callback():
    try:
        await discord.callback()
    except Exception:
        pass

    return redirect(
        url_for("dashboard")
    )  # dashboard function will be  created later in the a


@app.route("/add-sex", methods=["POST"])
@auth_required("POST")
async def add_sex(user):
    data = await request.get_json()
    sex_coll = motor_db["sex-gifs"]
    await sex_coll.insert_one(data)
    return "Sex Success", 200

@app.route("/remove-sex", methods=["POST"])
@auth_required("POST")
async def remove_sex(user):
    data = await request.get_json()
    print(f"received: {data}")
    sex_coll = motor_db["sex-gifs"]
    await sex_coll.delete_one({"_id": ObjectId(data['_id'])})
    return "Sex Removed", 200


@app.route("/add-footjob", methods=["POST"])
@auth_required("POST")
async def add_footjob(user):
    # user = await verify("POST")
    # if not isinstance(user, User):
        # return user

    data = await request.get_json()
    sex_coll = motor_db["footjob-gifs"]
    await sex_coll.insert_one(data)
    return "Footjob Success", 200

@app.route("/remove-footjob", methods=["POST"])
@auth_required("POST")
async def remove_footjob(user):
    data = await request.get_json()
    sex_coll = motor_db["footjob-gifs"]
    await sex_coll.delete_one({"_id": ObjectId(data['_id'])})
    return "Footjob Removed", 200


async def refresh_cdn(urls):
    """Refresh CDN urls and returns a dict of the mapping"""

    urls = [x["url"] for x in urls]

    endpoint = "https://discord.com/api/v9/attachments/refresh-urls"

    headers = {
        "Authorization": f'Bot {os.getenv("DISCORD_TOKEN")}',
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        payload = {"attachment_urls": urls}

        async with session.post(endpoint, json=payload, headers=headers) as resp:
            response_data = await resp.json()
            if resp.status == 200 or resp.status == 201:
                urls = response_data["refreshed_urls"]
                refreshed = {x["original"]: x["refreshed"] for x in urls}
                return refreshed
            else:
                print("Error sending message:", response_data)
                return None



    
@app.route("/dashboard")
@auth_required("GET")
async def dashboard(user):
    # guild_count = await ipc_client.request("get_guild_count") # get func we created aearlier for guild count
    # guild_ids = await ipc_client.request("get_guild_ids") # get func we created aearlier for guild IDs    
    # user = await verify("GET")
    # if not isinstance(user, User):
        # return user

    cdn_urls = []

    def gif_iterator(x, arr):
        if "cdn.discordapp.com" in x["url"]:
            arr.append(x)
        return x

    li = await motor_db["sex-gifs"].find().to_list()
    sex_urls = [gif_iterator(x, cdn_urls) for x in li]

    li = await motor_db["footjob-gifs"].find().to_list()
    footjob_urls = [gif_iterator(x, cdn_urls) for x in li]

    refresh_map = await refresh_cdn(cdn_urls)

    def update_urls(x):
        if x["url"] in refresh_map:
            x["url"] = refresh_map[x["url"]]
            return x
        return x

    sex_urls = [update_urls(x) for x in sex_urls]
    footjob_urls = [update_urls(x) for x in footjob_urls]

    return await render_template(
        "dashboard.html", user=user, sex_urls=sex_urls, footjob_urls=footjob_urls
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port="8082")
