from flask import Flask
from flask_apscheduler import APScheduler
from flask_sqlalchemy import SQLAlchemy
import logging
from logging.handlers import RotatingFileHandler
from tzlocal import get_localzone


app = Flask(__name__)
app.config.from_object('config')

# handler = RotatingFileHandler('app.log', maxBytes=10240, backupCount=5)
# handler.setLevel(logging.DEBUG)
# app.logger.addHandler(handler)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
# logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
logging.getLogger('apscheduler.scheduler').setLevel(logging.DEBUG if app.config['DEBUG'] else logging.INFO)
logging.getLogger('peewee').setLevel(logging.DEBUG if app.config['DEBUG'] else logging.INFO)
logging.getLogger('yfinance').setLevel(logging.DEBUG if app.config['DEBUG'] else logging.INFO)
logging.getLogger('apscheduler').setLevel(logging.DEBUG if app.config['DEBUG'] else logging.INFO)
logging.getLogger('urllib3').setLevel(logging.DEBUG if app.config['DEBUG'] else logging.INFO)


db = SQLAlchemy(app, engine_options={"connect_args": {"options":f'-c timezone={str(get_localzone())}'}})

scheduler = APScheduler()
scheduler.api_enabled = True
scheduler.init_app(app)
scheduler.start()
