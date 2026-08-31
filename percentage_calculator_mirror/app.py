"""
Percentage Calculator (Mirror)

A small local web-app mirror of the internal "Percentage Calculator" tool
used during premium adjustment review to calculate the percentage change
between two premium figures, built so a Robot Framework +
RPA.Browser.Selenium automation can be developed and tested against it
instead of a real production tool.

ALL data in this app is fictitious.

Run with:
    ~/rpa-env/bin/python app.py
Serves on http://127.0.0.1:5059 by default (override with PORT env var).
"""
import os

from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)

STATE = {"from_value": "", "to_value": "", "result": ""}


@app.route("/", methods=["GET"])
def home():
    return render_template("calculator.html", state=STATE)


@app.route("/calculate", methods=["POST"])
def calculate():
    from_raw = (request.form.get("from_value") or "").strip()
    to_raw = (request.form.get("to_value") or "").strip()
    STATE["from_value"] = from_raw
    STATE["to_value"] = to_raw
    try:
        from_num = float(from_raw)
        to_num = float(to_raw)
        pct = ((to_num - from_num) / from_num) * 100 if from_num else 0.0
        STATE["result"] = f"{pct:.2f}%"
    except ValueError:
        STATE["result"] = "Error"
    return redirect(url_for("home"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5059"))
    app.run(host="127.0.0.1", port=port, debug=False)
