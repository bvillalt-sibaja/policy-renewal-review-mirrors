"""
News Search (Mirror)

A small local web-app mirror of a Google/Edge-style news search, built so a
Robot Framework + RPA.Browser.Selenium automation can be developed and
tested against controllable, reproducible fictitious results instead of
hitting the real internet with dummy client names (which would return
irrelevant real-world results and make this demo non-reproducible).

ALL data in this app is fictitious. Nothing here represents a real news
search or a real person.

Run with:
    ~/rpa-env/bin/python app.py
Serves on http://127.0.0.1:5062 by default (override with PORT env var).
"""
import os

from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)

# Keyed by exact client name (case-insensitive) - the recorded "Research
# Client" step searches whatever name Outlook/EIGALPHA gave it, so this is
# looked up by name, not by policy number.
NEWS_RESULTS = {
    "mr j doe": "No news results found for \"Mr J Doe\".",
    "mrs a doe": (
        "Local Business Owner Faces Ongoing Legal Dispute - Regional Times, "
        "2 days ago - Mrs A Doe is reported to be involved in an ongoing "
        "legal complaint regarding a service dispute with a former "
        "contractor. The matter remains unresolved as of this report."
    ),
}

STATE = {"query": "", "news_tab": False, "results": ""}


@app.route("/", methods=["GET"])
def home():
    return render_template("news_search.html", state=STATE)


@app.route("/search", methods=["POST"])
def search():
    query = (request.form.get("query") or "").strip()
    STATE["query"] = query
    STATE["news_tab"] = False
    STATE["results"] = ""
    return redirect(url_for("home"))


@app.route("/news-tab", methods=["POST"])
def news_tab():
    STATE["news_tab"] = True
    STATE["results"] = NEWS_RESULTS.get(
        STATE["query"].strip().lower(), f'No news results found for "{STATE["query"]}".'
    )
    return redirect(url_for("home"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5062"))
    app.run(host="127.0.0.1", port=port, debug=False)
