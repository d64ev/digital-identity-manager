import json

from flask_basicauth import BasicAuth
import os
import string
import subprocess
from typing import List
import re

from flask import Flask, render_template, request, flash, redirect
import configparser

account_pattern = re.compile("https://(.*)/@?(.*)")


class InvalidStateException(BaseException):
    pass


app = Flask(__name__)


def twitter_accountname(url):
    return account_pattern.findall(url)[0][1]


def mastodon_accountname(url):
    print(account_pattern.findall(url))
    username = account_pattern.findall(url)[0][1]
    url = account_pattern.findall(url)[0][0]
    return f"{username}@{url}"


ACCOUNTS = [("mastodon", mastodon_accountname), ("twitter", twitter_accountname)]
RESERVED_NAMES = ["admin"]


def parse_config() -> dict:
    config = configparser.ConfigParser()
    config.read("settings.ini")
    return {
        "domain": config['DEFAULT']['Domain'],
        "path": config['DEFAULT']['Path'],
        "secret": config['DEFAULT']['Secret'],
        "port": config['DEFAULT']['Port'],
        "prefix": config['DEFAULT']['Prefix'],
        "website_dir": config['DEFAULT']['WebsitePath'],

    }


def get_auth() -> (str, str):
    config = configparser.ConfigParser()
    config.read("settings.ini")
    return config['Authentication']['Username'], config['Authentication']['Password']


CFG = parse_config()
RESERVED_NAMES = list(map(lambda x: f"{x}.{CFG['domain']}", RESERVED_NAMES))
app.secret_key = CFG['secret']

user, password = get_auth()
app.config['BASIC_AUTH_USERNAME'] = user
app.config['BASIC_AUTH_PASSWORD'] = password
app.config['BASIC_AUTH_FORCE'] = True
basic_auth = BasicAuth(app)


@app.route('/', methods=['GET'])
@basic_auth.required
def index():
    users = find_subdomains(CFG['path'], CFG['domain'])
    return render_template('base.html', existing_users=users, prefix=CFG['prefix'])


@app.route('/create', methods=['POST'])
@basic_auth.required
def create():
    users = find_subdomains(CFG['path'], CFG['domain'])

    username = request.form['username'].lower() + '.' + CFG['domain']

    if username in RESERVED_NAMES:
        flash(f"Reserved username.", category="error")
        return redirect(f"/{CFG['prefix']}", code=303)

    did = request.form['did']
    if did.startswith("did="):
        did = did[4:]
    if username in users:
        flash(f"User {username} does already exist!", category='error')
    elif not check_username(request.form['username']):
        flash(f"Username {username} does contain invalid characters! Only a-z0-9 and - "
              f"are allowed!", category='error')
    elif len(request.form['username']) > 63:
        flash(f"Username {username} is too long!", category='error')
    else:
        try:
            accounts = []
            if len(did) > 0:
                accounts.append(
                    {"service": "bluesky", "url": f"https://bsky.app/profile/{username}",
                     "name": username})
            for (service, fn_name) in ACCOUNTS:
                if len(request.form.get(service)) > 0:
                    account_url = request.form.get(service)
                    accounts.append({"service": service, "url": account_url,
                                     "name": fn_name(account_url)})

            create_user(username, did, accounts)
            flash(
                f"User {username} was created! Check out https://{username}/",
                category='success')
        except Exception as e:
            flash(f"Error on creating user: {e}", category="error")
    return redirect(f"/{CFG['prefix']}", code=303)


@app.route('/remove', methods=['POST'])
@basic_auth.required
def remove():
    users = find_subdomains(CFG['path'], CFG['domain'])

    username = request.form['username']

    if not username in users:
        flash(f"User {username} does not exist!", category='error')
    else:
        try:
            remove_user(username, CFG['path'])
            flash(f"User {username} was removed!", category='success')
        except Exception as e:
            flash(f"Error on removing user: {e}", category="error")
    return redirect(f"/{CFG['prefix']}", code=303)


def find_subdomains(path: str, domain: str) -> List[str]:
    subdomains = [d for d in os.listdir(path) if
                  os.path.isdir(path + '/' + d) and d.endswith(domain) and len(
                      domain) < len(d) and d not in RESERVED_NAMES]
    return subdomains


def check_username(base_name: str) -> bool:
    allowed = set(string.ascii_lowercase + string.digits + '-')
    return set(base_name) <= allowed


def create_user(username: str, did: str, accounts):
    os.makedirs(f"{CFG['path']}/{username}/.well-known")
    if len(did) > 0:
        with open(f"{CFG['path']}/{username}/.well-known/atproto-did", "w") as f:
            f.write(did)
    with open(f"{CFG['path']}/{username}/accounts.json", "w") as f:
        f.write(json.dumps(accounts))
    subprocess.run(f"/usr/bin/uberspace web domain add {username}", shell=True)
    with open("website/index.php", "r") as f:
        webpage = f.read()
    webpage = webpage.replace("$WEBSITE_DIR", CFG['website_dir'])
    with open(f"{CFG['path']}/{username}/index.php", "w") as f:
        f.writelines(webpage)


def try_rm(path):
    try:
        os.remove(path)
    except OSError:
        pass


def remove_user(username: str, path: str):
    try_rm(f"{path}/{username}/.well-known/atproto-did")
    try_rm(f"{path}/{username}/accounts.json")
    try_rm(f"{path}/{username}/index.php")

    os.rmdir(f"{path}/{username}/.well-known/")
    os.rmdir(f"{path}/{username}/")
    subprocess.run(f"/usr/bin/uberspace web domain del {username}", shell=True)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=CFG['port'])
