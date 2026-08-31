"""
Sample Insurer -- Map View (Mirror)

A small local web-app mirror of the internal GIS/"Map View" tool used to look
up a property's location during underwriting review, built so a Robot
Framework + RPA.Browser.Selenium automation can be developed and tested
against it instead of a real production GIS system.

ALL data in this app is fictitious. Nothing here represents a real insurer,
real property, or real production system.

Run with:
    ~/rpa-env/bin/python app.py
Serves on http://127.0.0.1:5058 by default (override with PORT env var).
"""
import os

from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)

# In-memory only - resets on restart. No persistence needed for this mirror.
STATE = {
    "address": "",
    "ad_hoc_analysis": False,
    "hybrid_view": False,
    "overlay": False,
}


@app.route("/", methods=["GET"])
def home():
    return render_template("map_view.html", state=STATE)


@app.route("/search", methods=["POST"])
def search():
    raw_address = (request.form.get("address") or "").strip()
    # Mirrors a real GIS tool geocoding/formatting whatever was typed into a
    # confirmed, canonical address - so the search bar's readback differs
    # slightly from the raw typed text, same as the real tool would.
    if raw_address:
        STATE["address"] = f"{raw_address} (confirmed location)"
    return redirect(url_for("home"))

@app.route("/ad-hoc-analysis", methods=["POST"])
def ad_hoc_analysis():
    STATE["ad_hoc_analysis"] = True
    return redirect(url_for("home"))


@app.route("/hybrid-view", methods=["POST"])
def hybrid_view():
    STATE["hybrid_view"] = not STATE["hybrid_view"]
    return redirect(url_for("home"))


@app.route("/overlay", methods=["POST"])
def overlay():
    STATE["overlay"] = not STATE["overlay"]
    return redirect(url_for("home"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5058"))
    app.run(host="127.0.0.1", port=port, debug=False)
