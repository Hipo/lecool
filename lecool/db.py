import datetime
import time
import pytz

from boto.dynamodb2.fields import HashKey, RangeKey, AllIndex
from boto.dynamodb2.table import Table
from boto.dynamodb2.types import NUMBER


AWS_REGION = "us-east-1"
AWS_ACCESS_KEY_ID = "AKIAIS7GWBD6B7FYAFKA"
AWS_SECRET_ACCESS_KEY = "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"
TABLE_NAME = "lecool_issues"
LOCAL_TIMEZONE = pytz.timezone("EST")


class DatabaseManager(object):
    """
    Database manager layer for DynamoDB
    """
    def __init__(self, connection, debug=False):
        super(DatabaseManager, self).__init__()

        self.connection = connection

        tables_list = self.connection.list_tables()

        if TABLE_NAME in tables_list.get("TableNames"):
            self.table = Table(table_name=TABLE_NAME, connection=self.connection)
        else:
            self.table = Table.create(TABLE_NAME, [
                HashKey("edition"), 
                RangeKey("issue_number", data_type=NUMBER)
            ], indexes=[
                AllIndex("IssueIndex", parts=[
                    HashKey("edition"), 
                    RangeKey("issue_number", data_type=NUMBER)
                ])
            ], connection=self.connection)


class Event(object):
    """
    A model for lecool issue events
    """
    def __init__(self, event_info):
        super(Event, self).__init__()

        self.map = event_info.get("map")
        self.description = event_info.get("description")
        self.title = event_info.get("title")
        self.image = event_info.get("image")
        self.longitude = event_info.get("longitude")
        self.latitude = event_info.get("latitude")
        self.location = event_info.get("location")
        self.time = event_info.get("time")
        self.type = event_info.get("type")
        self.price = event_info.get("price")

        date = event_info.get("date")

        if type(date) is str or type(date) is unicode:
            self.date = datetime.date(*[int(i) for i in date.split("-")])
        else:
            self.date = date

    def serialize(self):
        return {
            "map": self.map,
            "description": self.description,
            "title": self.title,
            "image": self.image,
            "longitude": self.longitude,
            "latitude": self.latitude,
            "location": self.location,
            "time": self.time,
            "type": self.type,
            "price": self.price,
            "date": self.date.isoformat() if self.date else None,
        }


class Issue(object):
    """
    A model for lecool issues
    """
    def __init__(self, issue_info):
        super(Issue, self).__init__()

        self.edition = issue_info.get("edition")
        self.issue_number = issue_info.get("issue_number")
        self.title = issue_info.get("title")
        self.url = issue_info.get("url")
        self.image = issue_info.get("image")

        start_date = issue_info.get("start_date")

        if type(start_date) is str or type(start_date) is unicode:
            self.start_date = datetime.date(*[int(i) for i in start_date.split("-")])
        else:
            self.start_date = start_date

        self.events = []

        for event_info in issue_info.get("events", []):
            self.events.append(Event(event_info))

    def serialize(self):
        return {
            "edition": self.edition,
            "issue_number": self.issue_number,
            "title": self.title,
            "url": self.url,
            "image": self.image,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "events": [e.serialize() for e in self.events],
        }
