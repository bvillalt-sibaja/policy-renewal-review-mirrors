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
import re

from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)

# Keyed by exact client name (case-insensitive) - the recorded "Research
# Client" step searches whatever name Outlook/EIGALPHA gave it, so this is
# looked up by name, not by policy number.
NEWS_RESULTS = {
    "mr j doe": "No news results found for \"Mr J Doe\".",
    "mrs a doe": [
        {
            "source": "Regional Times",
            "title": "Local Business Owner Faces Ongoing Legal Dispute",
            "snippet": (
                "Mrs A Doe is reported to be involved in an ongoing "
                "legal complaint regarding a service dispute with a former "
                "contractor. The matter remains unresolved as of this report."
            ),
            "age": "2 days ago",
        },
    ],
}


def all_tab_results(query):
    """Generic, fictitious web results shown on the "All" tab for any query.

    These are decorative only - the automation reads the News tab
    (id=search-results), never these."""
    q = query or "Search"
    slug = re.sub(r"[^a-z0-9]+", "-", q.lower()).strip("-") or "search"
    return [
        {"site": "Example Directory", "url": f"https://www.example-directory.test › people › {slug}",
         "title": f"{q} - Contact details and listings",
         "snippet": f"Find listings that match {q}. Browse publicly listed contact details, local businesses and directory entries in your area."},
        {"site": "Sample Business Register", "url": "https://register.sample-business.test › search",
         "title": f"{q} | Company officers and appointments",
         "snippet": f"Search the sample register for officers named {q}. View appointments, filing history and registered office addresses."},
        {"site": "Placeholder Reviews", "url": f"https://www.placeholder-reviews.test › {slug}",
         "title": f"Reviews mentioning {q}",
         "snippet": "Read customer reviews and ratings from people in the local community. Share your own experience and help others decide."},
        {"site": "Demo Social", "url": f"https://social.demo.test › {slug}",
         "title": f"{q} profiles | Demo Social",
         "snippet": f"View profiles for people named {q}. Join Demo Social to connect with friends, family and people you know."},
    ]


STATE = {"query": "", "news_tab": False, "results": ""}


@app.route("/", methods=["GET"])
def home():
    return render_template(
        "news_search.html", state=STATE, all_results=all_tab_results(STATE["query"])
    )


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
