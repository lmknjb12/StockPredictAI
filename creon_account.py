import json
import time
import win32com.client


FILE = "account.json"

INTERVAL = 5


cpCybos = win32com.client.Dispatch(
    "CpUtil.CpCybos"
)


if cpCybos.IsConnect != 1:
    print("Creon 연결 실패")
    exit()


trade = win32com.client.Dispatch(
    "CpTrade.CpTdUtil"
)


if trade.TradeInit() != 0:
    print("주문 초기화 실패")
    exit()


account = trade.AccountNumber[0]

goods = trade.GoodsList(
    account,
    1
)[0]


# 잔고 조회
balance = win32com.client.Dispatch(
    "CpTrade.CpTd6033"
)


def get_account():

    balance.SetInputValue(
        0,
        account
    )

    balance.SetInputValue(
        1,
        goods
    )

    balance.SetInputValue(
        2,
        50
    )


    balance.BlockRequest()


    cash = 0
    quantity = 0
    avg_price = 0


    # 종목 검색

    for i in range(
        balance.GetHeaderValue(5)
    ):

        code = balance.GetDataValue(
            12,
            i
        )


        if code == "A005930":

            quantity = balance.GetDataValue(
                7,
                i
            )

            avg_price = balance.GetDataValue(
                17,
                i
            )



    # 예수금 조회

    cash_obj = win32com.client.Dispatch(
        "CpTrade.CpTdNew5331A"
    )


    cash_obj.SetInputValue(
        0,
        account
    )

    cash_obj.SetInputValue(
        1,
        goods
    )

    cash_obj.BlockRequest()


    cash = cash_obj.GetHeaderValue(
        9
    )



    return {

        "cash": float(cash),

        "quantity": int(quantity),

        "avg_price": float(avg_price)

    }



while True:


    try:

        data=get_account()


        with open(
            FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                indent=4
            )


        print(
            data
        )


    except Exception as e:

        print(
            e
        )


    time.sleep(
        INTERVAL
    )