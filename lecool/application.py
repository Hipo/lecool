import logging

from boto import dynamodb2
from flask import Flask, render_template, request, url_for, redirect, Response, abort
from json import dumps

from werkzeug.contrib.fixers import ProxyFix

from db import DatabaseManager, Issue, AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
from parsers import parse_issue, data_handler


app = Flask(__name__)


@app.before_first_request
def setup_logging():
    if not app.debug:
        # In production mode, add log handler to sys.stderr.
        app.logger.addHandler(logging.StreamHandler())
        app.logger.setLevel(logging.INFO)
        
        db_connection = dynamodb2.connect_to_region(
            AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )

        app.db = DatabaseManager(db_connection)


@app.route("/")
def home():
    """
    Render landing page
    """
    return render_template("home.html", 
        
    )


@app.route("/issues/<issue_number>")
def detail(issue_number):
    """
    Render issue detail page
    """
    try:
        issue_number = int(issue_number)
    except ValueError:
        abort(404)

    try:
        issue = [Issue(i) for i in app.db.table.query(
            edition__eq="Istanbul",
            issue_number__eq=issue_number,
            index="IssueIndex",
        )][0]
    except:
        issue = None

    if issue is None:
        issue = parse_issue(issue_number)

        if issue:
            app.db.table.put_item(data=issue.serialize())

    if issue is None:
        abort(404)

    if request.args.get("format") == "json":
        return Response(
            response=dumps(issue, default=data_handler),
            status=200,
            mimetype="application/json",
        )
    else:
        return render_template("issue.html", issue=issue)


app.wsgi_app = ProxyFix(app.wsgi_app)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
