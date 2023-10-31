# D-64 Identity Service for Uberspace -- Proof of concept
Create a virtual environment and install the requirements in `venv/`.
Create a file `settings.ini` with the following values:

```
[DEFAULT]
Prefix=URL_SUBDIR/
Domain=YOUR_DOMAIN
Path=Path to your /var/www/virtual/USERNAME/ directory
Secret=A long, random string
Port=PORT
WebsitePath=Full path to the "website" directory of this repo

[Authentication]
username=USER
password=PASS
```

Host the stuff from the `index/` folder at your webserver.
Replace all paths leading to, e.g., a logo or CSS-file in `website/*` with your website hosting the `index/` stuff.
The index.php is later copied, so do not remove the `$WEBSITE_DIR`, it is later changed automatically.

Add it as uberspace backend:
`uberspace web backend set $URL/admin --http --remove-prefix --port PORT`