import re
import requests

from datetime import date
from lxml import html
from unidecode import unidecode
from urlparse import urlparse, parse_qs

from db import Issue


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


def parse_issue(issue_number):
    """
    Fetches and parses any issue
    """
    response = requests.get(LECOOL_ISSUE_URL % {
        "city": "istanbul",
        "country": "tr",
        "issue": issue_number,
    })

    if response.status_code != 200:
        return None

    doc = html.document_fromstring(response.text)
    head = doc.find("head")
    issue_info = {
        "issue_number": issue_number,
    }

    for meta in head.findall("meta"):
        if meta.attrib.get("property") == "og:url":
            issue_info.update({
                "url": meta.attrib.get("content")
            })
        elif meta.attrib.get("property") == "og:image":
            issue_info.update({
                "image": meta.attrib.get("content")
            })
        elif meta.attrib.get("property") == "og:title":
            issue_info.update({
                "title": meta.attrib.get("content")
            })
        elif meta.attrib.get("property") == "og:site_name":
            issue_info.update({
                "edition": meta.attrib.get("content").replace("LE COOL -", "").strip()
            })

    container = doc.cssselect("#container")[0]
    items = []
    start_date = None

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

            event_date = date(int(year), month_index, int(day))

            if start_date is None or event_date < start_date:
                start_date = event_date

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

    if start_date:
        issue_info.update({
            "start_date": start_date,
        })

    issue_info.update({
        "events": items,
    })

    return Issue(issue_info)


def data_handler(obj):
    if hasattr(obj, "serialize"):
        return obj.serialize()
    elif hasattr(obj, "isoformat"):
        return obj.isoformat()
    else:
        return obj
