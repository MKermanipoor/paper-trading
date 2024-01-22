from app import app
from app import models


@app.route('/')
def hello():

    return "Hello World!"

@app.route('/a')
def a():
    return f'{[_.title for _ in models.Account.query.all()]}'
    # return 'waofiho'
