from app.models import TestInfo, Order, Asset, Position
from app import app
import requests


def send_message(msg: str, chanel_id: int):
    requests.post(f'https://api.telegram.org/bot{app.config['BOT_TOKEN']}/sendMessage',
                  {
                      "chat_id": chanel_id,
                      "text": msg
                  })
    pass


def get_common_message(test_info: TestInfo.TestInfoDTO,
                       asset: Asset.AssetDTO,
                       order: Order,
                       position: Position) -> str:
    return (f'{"🛒 BUY" if position == Position.buy else "💰 SELL"}' +
            f'\nℹ️ Test: #Test_{test_info.id} {test_info.name}\n' +
            f'📈 Stock: #{asset.symbol}\n' +
            f'📄 Number of share: {order.shares}\n' +
            f'💲 Price: {order.average_price}\n' +
            f'🕰 Time: {order.filled_at}')


def send_buy_action_message(test_info: TestInfo.TestInfoDTO,
                            asset: Asset.AssetDTO,
                            order: Order):
    send_message(get_common_message(test_info, asset, order, Position.buy)
                 , test_info.setting[TestInfo.CHANNEL_ID_SETTING_KEY])


def send_sell_action_message(test_info: TestInfo.TestInfoDTO,
                             asset: Asset.AssetDTO,
                             order: Order):
    send_message(get_common_message(test_info, asset, order, Position.sell)
                 , test_info.setting[TestInfo.CHANNEL_ID_SETTING_KEY])

if __name__ == '__main__':
    send_message("test message", 75775194)
