import os

from boto import dynamodb2
from boto.dynamodb2.layer1 import DynamoDBConnection

from application import app
# from db import DatabaseManager, AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY


# db_connection = DynamoDBConnection(
#     aws_access_key_id="dummy_key",
#     aws_secret_access_key="dummy_secret",
#     host=os.environ["DYNAMODB_PORT_8000_TCP_ADDR"],
#     port=8000,
#     is_secure=False
# )

# db_connection = dynamodb2.connect_to_region(
#     AWS_REGION,
#     aws_access_key_id=AWS_ACCESS_KEY_ID,
#     aws_secret_access_key=AWS_SECRET_ACCESS_KEY
# )
#
# app.db = DatabaseManager(db_connection)
app.run(debug=True, host="0.0.0.0", port=5000)
