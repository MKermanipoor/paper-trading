import sys
from operator import and_
from time import sleep

from app import app, scheduler, models
from sqlalchemy.sql.functions import now


# from app import view


def test():
    with app.app_context():
        _ = models.TestInfo.query.filter(and_(models.TestInfo.start_time <= now(), models.TestInfo.end_time >= now()))
        print(f'{[(_.name, _.account.title) for _ in _]}')


def init_jobs():
    with app.app_context():
        valid_tests = models.TestInfo.query.filter(and_(models.TestInfo.start_time <= now(),
                                                        models.TestInfo.end_time >= now())).all()
        app.logger.info(f'found {len(valid_tests)} tests')
        from bot import add_test_jobs
        for t in valid_tests:
            add_test_jobs(t, scheduler)
            # b = Bot(t)
            # setting = t.interval.copy()
            # setting['args'] = [b]
            # scheduler.add_job(f'bot {t.id}', call_bot, **setting)


if __name__ == "__main__":
    print('called')
    # while True:
    #     sleep(1)
    init_jobs()
    param = {
        'trigger': 'cron',
        'second': '*/2'
    }
    # scheduler.add_job('id', test, **param)
    app.run(host=sys.argv[1], use_reloader=False)
