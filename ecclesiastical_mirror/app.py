"""
Ecclesiastical Post Code Look Up (Mirror)

A small local web-app mirror of the internal post-code lookup page used to
confirm a property's address/location during underwriting review, built so
a Robot Framework + RPA.Browser.Selenium automation can be developed and
tested against it instead of a real production site.

ALL data in this app is fictitious - no association with any real company
or system despite the reused name.

Run with:
    ~/rpa-env/bin/python app.py
Serves on http://127.0.0.1:5063 by default (override with PORT env var).
"""
import os

from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)

# Small dummy postcode -> address lookup table. Only one entry is needed for
# this project's test data (61 Rosslyn Hill) - any other postcode gets a
# generic "not found" result rather than crashing.
POSTCODE_DIRECTORY = {
    "NW3 1NL": "61 Rosslyn Hill, Hampstead, London NW3 1NL",
}

STATE = {"postcode": "", "result": ""}


@app.route("/", methods=["GET"])
def home():
    return render_template("postcode_lookup.html", state=STATE)


@app.route("/search", methods=["POST"])
def search():
    postcode = (request.form.get("postcode") or "").strip().upper()
    STATE["postcode"] = postcode
    STATE["result"] = POSTCODE_DIRECTORY.get(postcode, "No address found for this postcode.")
    return redirect(url_for("home"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5063"))
    app.run(host="127.0.0.1", port=port, debug=False)
