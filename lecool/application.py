import logging
import os
import re
import requests
import time

from boto import dynamodb2
from datetime import datetime
from flask import Flask, render_template, request, url_for, redirect, Response, abort
from json import dumps
from lxml import html
from unidecode import unidecode
from urlparse import urlparse, parse_qs

# from db import DatabaseManager, Channel, AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY


LECOOL_ISSUE_URL = "http://%(city)s.lecool.com/%(city)s/%(country)s/issue/%(issue)d"
DATE_RE = re.compile(r"(?P<month>.+) (?P<day>\d{2}) (?P<year>\d{4})")
TR_MONTH_MAP = ["ocak", "subat", "mart", "nisan", "mayis", "haziran", "temmuz", "agustos", "eylul", "ekim", "kasim", "aralik"]
EN_MONTH_MAP = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]

META_MAP = {
    "ne zaman": "time",
    "nerede": "location",
    "ne kadar": "price",
}

TR_CATEGORY_MAP = {
    "ozel gosterim": "screening",
    "tiyatro": "theatre",
    "konser": "concert",
    "parti": "party",
    "dj set": "dj",
    "yasam": "lifestyle",
    "sinema": "film",
    "resital": "recital",
    "performans": "performance",
    "sergi": "artshow",
}


app = Flask(__name__)


def date_handler(obj):
    return obj.isoformat() if hasattr(obj, 'isoformat') else obj


@app.before_first_request
def setup_logging():
    if not app.debug:
        # In production mode, add log handler to sys.stderr.
        app.logger.addHandler(logging.StreamHandler())
        app.logger.setLevel(logging.INFO)
        
        # db_connection = dynamodb2.connect_to_region(
        #     AWS_REGION,
        #     aws_access_key_id=AWS_ACCESS_KEY_ID,
        #     aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        # )
        #
        # app.db = DatabaseManager(db_connection)


@app.route("/")
def home():
    """
    Render landing page
    """
    return render_template("test.html", 
        
    )


@app.route("/issues/<issue>")
def detail(issue):
    """
    Render issue detail page
    """
    try:
        issue = int(issue)
    except ValueError:
        abort(404)

    response = requests.get(LECOOL_ISSUE_URL % {
        "city": "istanbul",
        "country": "tr",
        "issue": issue,
    })

    if response.status_code != 200:
        abort(404)

    doc = html.document_fromstring(response.text)
    container = doc.cssselect("#container")[0]
    items = []

    for td in container.cssselect("table[width='434']"):
        left_rows = td.cssselect("td[width='162']")
        right_rows = td.cssselect("td[width='272']")

        meta_info = {}
        date_info = left_rows[0].find("span")

        if date_info is not None:
            date_str = date_info.text.strip()
            month, day, year = DATE_RE.search(date_str).groups()

            try:
                month_index = TR_MONTH_MAP.index(unidecode(unicode(month)).lower()) + 1
            except ValueError:
                month_index = EN_MONTH_MAP.index(unidecode(unicode(month)).lower()) + 1

            event_date = datetime(int(year), month_index, int(day))

            meta_info.update({
                "date": event_date,
            })

        info_container = left_rows[1]
        active_meta_key = None
        active_info = ""

        if info_container is not None:
            for obj in info_container:
                if obj.tag == "img":
                    meta_info.update({
                        "image": obj.attrib.get("src")
                    })
                    
                    continue
                elif obj.tag == "a":
                    obj_href = obj.attrib.get("href")

                    if "maps.google.com" in obj_href:
                        map_url = urlparse(obj_href)
                        coords = parse_qs(map_url.query).get("sll")

                        if coords and len(coords) > 0:
                            lat, lon = coords[0].split(",")

                            meta_info.update({
                                "latitude": lat,
                                "longitude": lon,
                            })

                        meta_info.update({
                            "map": obj_href,
                        })
                    
                    continue
                elif obj.tag == "span":
                    new_meta_key = META_MAP.get(obj.text.strip())

                    if new_meta_key is None:
                        if obj.text:
                            active_info += obj.text

                        if obj.tail:
                            active_info += obj.tail

                        continue

                    if active_meta_key:
                        meta_info.update({
                            active_meta_key: active_info.strip(),
                        })

                    active_meta_key = new_meta_key
                    active_info = ""
                    continue
                elif active_meta_key:
                    if obj.text:
                        active_info += obj.text

                    if obj.tail:
                        active_info += obj.tail

            if active_meta_key:
                active_info = active_info.strip()

                if active_info == "-" or len(active_info) == 0:
                    active_info = None

                meta_info.update({
                    active_meta_key: active_info,
                })

        title_img = right_rows[0].find("img")
        spans = right_rows[1].findall("span")

        for span in spans:
            span_value = span.text.strip()

            if (spans.index(span) == 0):
                meta_key = "type"

                if "titles_other" in title_img.attrib.get("src"):
                    span_value = "location"
                else:
                    category_match = TR_CATEGORY_MAP.get(unidecode(unicode(span_value)).lower())

                    if category_match:
                        span_value = category_match
            else:
                meta_key = "title"

            meta_info.update({
                meta_key: span_value,
            })

        desc_container = right_rows[1].find("p")
        desc = desc_container.text

        for obj in desc_container:
            if obj.tag == "a":
                desc += "<a href=\"%s\">" % obj.attrib.get("href")
                desc += obj.text_content()
                desc += "</a>"
            elif obj.text is not None:
                desc += obj.text

            if obj.tail is not None:
                desc += obj.tail

        meta_info.update({
            "description": desc.strip(),
        })

        items.append(meta_info)

    if request.args.get("format") == "json":
        return Response(
            response=dumps({
                "items": items,
            }, default=date_handler),
            status=200,
            mimetype="application/json",
        )
    else:
        return render_template("issue.html", 
            items=items,
        )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
