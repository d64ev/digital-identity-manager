import json

from flask_basicauth import BasicAuth
import os
import string
import subprocess
from typing import List
import re

from flask import Flask, render_template, request, flash, redirect
import configparser

ACCOUNTS = ["mastodon", "twitter"]

account_pattern = re.compile("https://.*/@?(.*)")

class InvalidStateException(BaseException):
    pass


app = Flask(__name__)

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

cfg = parse_config()
app.secret_key = cfg['secret']

user, password = get_auth()
app.config['BASIC_AUTH_USERNAME'] = user
app.config['BASIC_AUTH_PASSWORD'] = password
app.config['BASIC_AUTH_FORCE'] = True
basic_auth = BasicAuth(app)



@app.route('/', methods=['GET'])
@basic_auth.required
def index():
    cfg = parse_config()
    users = find_subdomains(cfg['path'], cfg['domain'])
    return render_template('base.html', existing_users=users, prefix=cfg['prefix'])


@app.route('/create', methods=['POST'])
@basic_auth.required
def create():
    cfg = parse_config()
    users = find_subdomains(cfg['path'], cfg['domain'])

    username = request.form['username'].lower() + '.' + cfg['domain']
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
            accounts = [{ "service": "bluesky", "url": f"https://bsky.app/profile/{username}", "name": username}]
            for a in ACCOUNTS:
                if len(request.form.get(a)) > 0:
                    account_url = request.form.get(a)
                    accounts.append({ "service": a, "url": account_url, "name": account_pattern.findall(account_url)[0]})

            create_user(username, did, cfg['path'], accounts, cfg['website_dir'])
            flash(
                f"User {username} was created! Check out https://{username}/",
                category='success')
        except Exception as e:
            flash(f"Error on creating user: {e}", category="error")
    return redirect(f"/{cfg['prefix']}", code=303)


@app.route('/remove', methods=['POST'])
@basic_auth.required
def remove():
    cfg = parse_config()
    users = find_subdomains(cfg['path'], cfg['domain'])

    username = request.form['username']

    if not username in users:
        flash(f"User {username} does not exist!", category='error')
    else:
        try:
            remove_user(username, cfg['path'])
            flash(f"User {username} was removed!", category='success')
        except Exception as e:
            flash(f"Error on removing user: {e}", category="error")
    return redirect(f"/{cfg['prefix']}", code=303)




def find_subdomains(path: str, domain: str) -> List[str]:
    subdomains = [d for d in os.listdir(path) if
                  os.path.isdir(path + '/' + d) and d.endswith(domain) and len(
                      domain) < len(d)]
    for user in subdomains:
        if not os.path.isfile(f"{path}/{user}/.well-known/atproto-did"):
            flash(
                f"User {user} does not have a bsky-did at {user}/.well-known/atproto-did!", category="error")

    return subdomains


def check_username(base_name: str) -> bool:
    allowed = set(string.ascii_lowercase + string.digits + '-')
    return set(base_name) <= allowed


def create_user(username: str, did: str, path: str, accounts, website_dir):
    os.makedirs(f"{path}/{username}/.well-known")
    with open(f"{path}/{username}/.well-known/atproto-did", "w") as f:
        f.write(did)
    with open(f"{path}/{username}/accounts.json", "w") as f:
        f.write(json.dumps(accounts))
    subprocess.run(f"/usr/bin/uberspace web domain add {username}", shell=True)
    with open("website/index.php", "r") as f:
        webpage = f.read()
    webpage = webpage.replace("$WEBSITE_DIR", website_dir)
    with open(f"{path}/{username}/index.php", "w") as f:
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
    app.run(host='0.0.0.0', port=cfg['port'])
