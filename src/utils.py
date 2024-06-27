import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

import pandas as pd
import requests
from logger import logger_setup

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path_log = os.path.join(current_dir, "../logs", "utils.log")
logger = logger_setup("utils", file_path_log)


# Веб страница главное
def get_read_excel(file_path: str) -> List[Dict]:
    """Функция принимает путь до xlsx файла и создает список словарей с транзакциями"""
    try:
        data = pd.read_excel(file_path)
        logger.info("файл перекодирован")
        return data.to_dict(orient='records')
    except Exception as e:
        print(f"Ошибка {e}")
        logger.error(f"Ошибка {e}")
        return []

def get_greeting() -> str:
    """Функция определяет время суток и выводит приветствие соответствующее определённому времени"""
    current_time = datetime.datetime.now()
    if 6 <= current_time.hour < 12:
        logger.info("Приветствие утра")
        return "Доброе утро!"
    elif 12 <= current_time.hour < 18:
        logger.info("Приветствие дня")
        return "Добрый день!"
    elif 18 <= current_time.hour < 23:
        logger.info("Приветствие вечера")
        return "Добрый вечер!"
    else:
        logger.info("Приветствие ночи")
        return "Доброй ночи!"


def filter_transactions_by_date(transactions: list[dict], input_date_str: str) -> list[dict]:
    """Функция фильтрует транзакции с начала месяца до заданной дате."""
    input_date = datetime.strptime(input_date_str, "%d.%m.%Y")
    end_date = input_date + timedelta(days=1)
    start_date = datetime(end_date.year, end_date.month, 1)

    def parse_date(date_str: str) -> datetime:
        """Функция переводит дату из формата строки в формат datetime"""
        return datetime.strptime(date_str, "%d.%m.%Y %H:%M:%S")

    filtered_transactions = [
        transaction
        for transaction in transactions
        if start_date <= parse_date(transaction["Дата операции"]) <= end_date]
    logger.info(f"Транзакции в списке отфильтрованы по датам от {start_date} до {end_date}")
    return filtered_transactions

def get_cards_info(transactions: list[dict]) -> list[dict]:
    """Функция получает номера карт, общую сумму расходов и кэшбек"""
    card_data = {}
    for transaction in transactions:
        card_number = transaction.get("Номер карты")
        if not card_number or str(card_number).strip().lower() == "nan":
            continue
        amount = float(transaction["Сумма операции"])
        if card_number not in card_data:
            card_data[card_number] = {"total_spent": 0.0, "cashback": 0.0}
        if amount < 0:
            card_data[card_number]["total_spent"] += abs(amount)
            cashback_value = transaction.get("Кэшбэк")
            if transaction["Категория"] != "Переводы" and transaction["Категория"] != "Наличные":
                if cashback_value is not None:
                    cashback_amount = float(cashback_value)
                    if cashback_amount >= 0:
                        card_data[card_number]["cashback"] += cashback_amount
                    else:
                        card_data[card_number]["cashback"] += amount * -0.01
                else:
                    card_data[card_number]["cashback"] += amount * -0.01
    logger.info("Выполнен подсчёт кэшбека и суммы по картам")
    cards_data = []
    for last_digits, data in card_data.items():
        cards_data.append(
            {
                "last_digits": last_digits,
                "total_spent": round(data["total_spent"], 2),
                "cashback": round(data["cashback"], 2),
            }
        )
    logger.info("Получение словаря по тратам и кешбеку по каждой карте")
    return cards_data


def get_top_5_transactions(transactions: List[Dict]) -> List[Dict]:
    """Функция принимающая список транзакций, выводит топ 5 операций по платежу"""
    sorted_transactions = sorted(transactions, key=lambda x: abs(float(x["Сумма операции"])), reverse=True)
    top_5_sorted_transactions = []
    for transaction in sorted_transactions[:5]:
        date = datetime.strptime(transaction["Дата операции"], "%d.%m.%Y %H:%M:%S").strftime("%d.%m.%Y")
        top_5_sorted_transactions.append(
            {
                "date": date,
                "amount": transaction["Сумма операции"],
                "category": transaction["Категория"],
                "description": transaction["Описание"],
            }
        )
    logger.info("Выделен топ 5 транзакций по сумме")
    return top_5_sorted_transactions


def get_exchange_rates(currencies: List[str], api_key_currency: str) -> List[Dict]:
    """Функция которая принимает список кодов валют, возвращает список словарей с валютами и их курсами"""
    exchange_rates = []
    for currency in currencies:
        url = f"https://v6.exchangerate-api.com/v6/{api_key_currency}/latest/{currency}"
        response = requests.get(url)
        logger.info("Выполнен запрос на курс валют")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Получен ответ от api курса валют: {data}")
            ruble_cost = data["conversion_rates"]["RUB"]
            exchange_rates.append({"currency": currency, "rate": ruble_cost})
        else:
            print(f"Ошибка: {response.status_code}, {response.text}    1")
            logger.error(f"Ошибка api запроса {response.status_code}, {response.text}")
            exchange_rates.append({"currency": currency, "rate": None})
    logger.info("Курсы валют созданы")
    return exchange_rates


def get_stocks_cost(companies: List[str], api_key_stocks: str) -> List[Dict]:
    """Функция принимающая список кодов компаний, возвращает словарь со стоимостью акций каждой компании"""
    stocks_cost = []
    for company in companies:
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={company}&apikey={api_key_stocks}"
        response = requests.get(url)
        logger.info("Выполнен запрос на курс акций")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Получен ответ от api курса акций: {data}")
            time_series = data.get("Time Series (Daily)")
            if time_series:
                latest_date = max(time_series.keys())
                latest_data = time_series[latest_date]
                stock_cost = latest_data["4. close"]
                stocks_cost.append({"stock": company, "price": float(stock_cost)})
            else:
                print(f"Ошибка: данные для компании {company} недоступны. API ответ {data}")
                logger.error(f"Ошибка ответа: {data}")
                stocks_cost.append({"stock": company, "price": None})
        else:
            print(f"Ошибка: {response.status_code}, {response.text}    2")
            logger.error(f"Ошибка api запроса {response.status_code}, {response.text}")
            stocks_cost.append({"stock": company, "price": None})
    logger.info("Стоимость акций создана")
    return stocks_cost


# Веб страница события

def process_expenses(df: pd.DataFrame) -> dict[str, Any]:
    """Функция сортировки трат по категории и убыванию"""
    total_expenses = round(df["Сумма операции"].apply(lambda x: abs(x)).sum(), 0)

    grouped = df.groupby("Категория").agg({"Сумма операции": "sum"})
    main_categories = grouped.nlargest(7, "Сумма операции")
    other_categories_sum = grouped[~grouped.index.isin(main_categories.index)].sum()
    main_categories.loc["Остальное"] = other_categories_sum
    main_categories = main_categories.reset_index().to_dict(orient="records")

    transfers_and_cash = (
        df[df["Категория"].isin(["Переводы", "Наличные"])]
        .groupby("Категория")
        .agg({"Сумма операции": "sum"})
        .reset_index()
        .to_dict(orient="records")
    )
    result_expenses = {
        "total_amount": total_expenses,
        "main": main_categories,
        "transfers_and_cash": transfers_and_cash,
    }
    return result_expenses


def process_income(df: pd.DataFrame) -> dict:
    """Функция принимающая список словарей выполняет его сортировку по убыванию и выводит общую сумму, топ 3 категории
    по убыванию и выводит категории и кэшбэк"""
    total_income = round(df["Сумма операции"].apply(lambda x: abs(x)).sum(), 0)

    main_categories = (
        df.groupby("Категория")
        .agg({"Сумма операции": "sum"})
        .nlargest(3, "Сумма операции")
        .reset_index()
        .to_dict(orient="records")
    )
    result_income = {"total_amount": total_income, "main": main_categories}
    return result_income


def process_expenses_and_income(file_path: Any, date_str: Any, range_type: str = "M") -> pd.DataFrame:
    """Функция принимающет на вход строку с датой и второй необязательный параметр — диапазон данных"""
    df = pd.read_excel(file_path)

    df["Дата операции"] = pd.to_datetime(df["Дата операции"], format="%d.%m.%Y %H:%M:%S")
    df["Дата платежа"] = pd.to_datetime(df["Дата платежа"], format="%d.%m.%Y")

    date = datetime.strptime(date_str, "%d.%m.%Y")
    if range_type == "W":
        start_date = date - timedelta(days=date.weekday())
        end_date = start_date + timedelta(days=6)
    elif range_type == "M":
        start_date = datetime(date.year, date.month, 1)
        end_date = datetime(date.year, date.month, pd.Period(date, "M").days_in_month)
    elif range_type == "Y":
        start_date = datetime(date.year, 1, 1)
        end_date = datetime(date.year, 12, 31)
    elif range_type == "ALL":
        start_date = datetime(2000, 1, 1)
        end_date = date
    else:
        raise ValueError("Invalid range type")

    df = df[(df["Дата операции"] >= start_date) & (df["Дата операции"] <= end_date)]

    return df


def final_processing(result_expenses: Any, result_income: Any) -> str:
    """Функция которая возвращающет Json-ответ"""
    result_final = {"expenses": result_expenses, "income": result_income}
    return json.dumps(result_final, ensure_ascii=False, indent=4)
