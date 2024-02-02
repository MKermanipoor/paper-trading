from sqlalchemy import and_

from app.models import TestInfo, Rule, Position, Order, Asset, AssetBudget
from app import app, scheduler
from flask_apscheduler import APScheduler
import pandas as pd
import Market
import signal_util
from datetime import datetime
from telegram import send_buy_action_message, send_sell_action_message, send_message

WAIT_STATE = 'wait'
FREEZE_STATE = 'freeze_after_buy'
HOLD_STATE = 'hold'

def cast_database_result_to_df(database_result: list) -> pd.DataFrame:
    df = pd.DataFrame([vars(item) for item in database_result])
    df = df[database_result[0].__mapper__.columns.keys()]
    return df


class Bot:
    def __init__(self, test_info: TestInfo, buy_rule: Rule, sell_rule: Rule, asset: Asset):
        self.__test_info = test_info.get_DTO()

        self.__buy_rule = buy_rule.get_DTO()
        self.__sell_rule = sell_rule.get_DTO()
        self.__asset = asset.get_DTO()

        self.__account = test_info.account.get_DTO()

        result: Order = Order.query.filter(Order.rule_id.in_([self.__buy_rule.id, self.__sell_rule.id]))\
            .order_by(Order.action_time.desc())\
            .first()

        self.__state = HOLD_STATE
        if result is None:
            self.__state = WAIT_STATE

        elif not result.filled_at:
            self.__register_the_monitoring_order_job(result.alpaca_id)

        elif result.type == Position.buy:
            self.__state = HOLD_STATE
        else:
            self.__state = WAIT_STATE

        self.__budget_id = (AssetBudget.query.filter(and_(AssetBudget.asset_id == asset.id,
                                                        AssetBudget.test_id == test_info.id))
                          .first()).id

    def __register_the_monitoring_order_job(self, order_alpaca_id: str):
        self.__waiting_order_alpaca_id = order_alpaca_id
        self.__retry_counter = 0
        self.__state = FREEZE_STATE
        scheduler.add_job(self.__get_waiting_job_id(), self.wait_for_order_to_fulfill, trigger='interval', seconds=5)

    def __get_waiting_job_id(self):
        return f'waiting order job {self.__waiting_order_alpaca_id}'

    def wait_for_order_to_fulfill(self):
        order_response = Market.get_order_detail(self.__account, self.__waiting_order_alpaca_id)

        if not order_response['status'] == 'filled':
            self.__retry_counter += 1
            if self.__retry_counter >= 20:
                with app.app_context():
                    order = Order.query.filter(Order.alpaca_id == self.__waiting_order_alpaca_id).first()
                    self.__state = WAIT_STATE if order.type == Position.buy else HOLD_STATE
                    Order.query.session.delete(order)
                    Order.query.session.commit()

                Market.cancel_order(self.__account, self.__waiting_order_alpaca_id)
                scheduler.remove_job(self.__get_waiting_job_id())
            return

        order = Market.cast_to_order(order_response)
        with app.app_context():
            Order.query.filter(Order.alpaca_id == self.__waiting_order_alpaca_id) \
                .update({Order.shares: order.shares,
                         Order.average_price: order.average_price,
                         Order.filled_at: order.filled_at})
            Order.query.session.commit()

        scheduler.remove_job(self.__get_waiting_job_id())

        if order.type == Position.buy:
            self.__post_buy(order.to_DTO())
        else:
            self.__post_sell(order.to_DTO())


    def do_buy(self):
        if self.__state == HOLD_STATE or self.__state == FREEZE_STATE:
            app.logger.info(f'test {self.__test_info.name} asset {self.__asset.symbol}:\tpassed the buy, since it is in {self.__state} state')
            return

        candles = Market.get_candles(self.__asset.symbol, self.__test_info.setting[TestInfo.INTERVAL_SETTING_KEY])
        # todo check is data valida to do the transactions, week ends, out of market time
        buy_signal = signal_util.get_majority_signal(candles, self.__buy_rule.setting['signals'])
        sell_signal = signal_util.get_majority_signal(candles, self.__sell_rule.setting['signals'])
        if buy_signal.iloc[-1] and not sell_signal.iloc[-1]:
            app.logger.debug(f'test {self.__test_info.name} asset {self.__asset.symbol}: start buying')
            self.__state = FREEZE_STATE
            with app.app_context():
                budget: AssetBudget = AssetBudget.query.get(self.__budget_id)
                order = Market.create_order(self.__account, self.__asset.symbol, Position.buy, price_amount=int(budget.budget))
                if order is None:
                    self.__state = WAIT_STATE
                    app.logger.warning(f'test {self.__test_info.name} asset {self.__asset.symbol}:\tbot want\'s to buy, but it was unsucessfull')
                    return

                order.rule_id = self.__buy_rule.id
                Order.query.session.add(order)
                Order.query.session.commit()
                self.__register_the_monitoring_order_job(order.alpaca_id)

            app.logger.info(f'test {self.__test_info.name} asset {self.__asset.symbol}:\tbuy')

    def __post_buy(self, order: Order.OrderDTO):
        with app.app_context():
            AssetBudget.query.filter(AssetBudget.id == self.__budget_id).update(
                {AssetBudget.budget: AssetBudget.budget - order.shares * order.average_price})
            AssetBudget.query.session.commit()

        send_buy_action_message(self.__test_info, self.__asset, order)

        app.logger.info(f'test {self.__test_info.name} asset {self.__asset.symbol}:\tbuy fulfilled ')
        self.__state = HOLD_STATE

    def do_sell(self):
        if self.__state == WAIT_STATE or self.__state == FREEZE_STATE:
            app.logger.debug(f'test {self.__test_info.name} asset {self.__asset.symbol}:\tpassed the sell, since it is in {self.__state} state')
            return

        candles = Market.get_candles(self.__asset.symbol, self.__test_info.setting[TestInfo.INTERVAL_SETTING_KEY])
        # todo check is data valida to do the transactions, week ends, out of market time
        sell_signal = signal_util.get_majority_signal(candles, self.__sell_rule.setting['signals'])
        buy_signal = signal_util.get_majority_signal(candles, self.__buy_rule.setting['signals'])
        if sell_signal.iloc[-1] and not buy_signal.iloc[-1]:
            app.logger.debug(f'test {self.__test_info.name} asset {self.__asset.symbol}: start selling')
            with app.app_context():
                last_order: Order = Order.query.filter(Order.rule_id == self.__buy_rule.id).order_by(Order.action_time.desc()).first()
                order = Market.create_order(self.__account, self.__asset.symbol, Position.sell, number_of_share=last_order.shares)
                order.rule_id = self.__sell_rule.id
                Order.query.session.add(order)
                Order.query.session.commit()
                self.__register_the_monitoring_order_job(order.alpaca_id)

            app.logger.info(f'test {self.__test_info.name} asset {self.__asset.symbol}:\tsell')

    def __post_sell(self, order: Order.OrderDTO):
        with app.app_context():
            AssetBudget.query.filter(AssetBudget.id == self.__budget_id).update(
                {AssetBudget.budget: AssetBudget.budget + order.shares * order.average_price})
            AssetBudget.query.session.commit()

        send_sell_action_message(self.__test_info, self.__asset, order)

        app.logger.info(f'test {self.__test_info.name} asset {self.__asset.symbol}:\tsell fulfilled')
        self.__state = WAIT_STATE


class BotGroup:
    def __init__(self, test_info: TestInfo):
        self.__test_info = test_info.get_DTO()
        self.__account = test_info.account.get_DTO()
        rules = test_info.rules
        rules_df = cast_database_result_to_df(rules)

        rules_by_asset = rules_df.groupby(Rule.asset_id.key)
        self.__bots = {}
        for asset_id, asset_rules in rules_by_asset:
            buy_rule = asset_rules[asset_rules[Rule.position.key] == Position.buy]
            if buy_rule is None:
                raise f'buy rule for asset {asset_id} not found'
            if len(buy_rule) > 1:
                raise f'find more than one buy rule for asset {asset_id}'
            buy_rule: Rule = rules[buy_rule.index[0]]

            sell_rule = asset_rules[asset_rules[Rule.position.key] == Position.sell]
            if sell_rule is None:
                raise f'sell rule for asset {asset_id} not found'
            if len(sell_rule) > 1:
                raise f'find more than one sell rule for asset {asset_id}'
            sell_rule: Rule = rules[sell_rule.index[0]]

            self.__bots[asset_id] = Bot(test_info, buy_rule, sell_rule, buy_rule.asset)

    def get_position_schedule_name(self, position: Position):
        return self.__test_info.name + ' ' + position.name

    def setup_job(self, scheduler: APScheduler):
        __ = dict(self.__test_info.buy_interval)
        __['max_instances'] = 5
        scheduler.add_job(self.get_position_schedule_name(Position.buy), self._do_buy_job, **__)

        __ = dict(self.__test_info.sell_interval)
        __['max_instances'] = 5
        scheduler.add_job(self.get_position_schedule_name(Position.sell), self._do_sell_job, **__)

        scheduler.add_job(self.__test_info.name + ' reporter', self.__report_performance, trigger='cron',
                          hour=16,
                          day_of_week="mon-fri")

    def _do_buy_job(self):
        if not self._is_valid_time():
            return

        for b in self.__bots.values():
            b.do_buy()

    def _do_sell_job(self):
        if not self._is_valid_time():
            return

        for b in self.__bots.values():
            b.do_sell()

    def _is_valid_time(self) -> bool:
        now = datetime.now()
        if self.__test_info.start_time >= now or self.__test_info.end_time <= now:
            with app.app_context():
                scheduler.pause_job(self.get_position_schedule_name(Position.buy))
                scheduler.pause_job(self.get_position_schedule_name(Position.sell))
                app.logger.warning(f'{self.__test_info} is stopped due to finished test time')
            return False
        return True

    def __report_performance(self):
        performances = Market.get_performance(self.__account, 5)
        message = 'Strategy report:\n'
        for p in performances:
            message += f'{p.get_date()}:\t{"🟩" if p.get_profit_loss() > 0 else "🟥"} {p.get_profit_loss()}$\n'
        message += '#report'

        send_message(message, self.__test_info.setting[TestInfo.CHANNEL_ID_SETTING_KEY])

def add_test_jobs(test_info: TestInfo, scheduler: APScheduler):
    bot_group = BotGroup(test_info)
    bot_group.setup_job(scheduler)
