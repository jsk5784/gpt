from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import os
import time as time_module
from urllib import request, parse

# Simple Korean holiday calendar for 2024 (limited set)
HOLIDAYS_2024 = {
    date(2024, 1, 1),
    date(2024, 2, 9), date(2024, 2, 10), date(2024, 2, 11), date(2024, 2, 12),
    date(2024, 3, 1),
    date(2024, 5, 5), date(2024, 5, 6),
    date(2024, 5, 15),
    date(2024, 6, 6),
    date(2024, 8, 15),
    date(2024, 9, 16), date(2024, 9, 17), date(2024, 9, 18),
    date(2024, 10, 3),
    date(2024, 10, 9),
    date(2024, 12, 25),
}

@dataclass
class Event:
    time: datetime
    message: str
    sent: bool = False

class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id

    def send_message(self, text: str):
        if not self.token or not self.chat_id:
            print(f"[Telegram disabled] {text}")
            return
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        data = parse.urlencode({"chat_id": self.chat_id, "text": text}).encode()
        req = request.Request(url, data=data)
        try:
            request.urlopen(req)
        except Exception as e:
            print(f"Failed to send Telegram message: {e}")

def is_holiday(d: date) -> bool:
    if d.year == 2024:
        return d in HOLIDAYS_2024
    return False

def is_weekend(d: date) -> bool:
    return d.weekday() >= 5


def is_business_day(d: date) -> bool:
    return not is_weekend(d) and not is_holiday(d)

def previous_business_day(d: date) -> date:
    cur = d - timedelta(days=1)
    while not is_business_day(cur):
        cur -= timedelta(days=1)
    return cur

def next_business_day(d: date) -> date:
    cur = d + timedelta(days=1)
    while not is_business_day(cur):
        cur += timedelta(days=1)
    return cur

def end_of_nonbusiness_period(start: date) -> date:
    cur = start
    while True:
        nxt = cur + timedelta(days=1)
        if is_weekend(nxt) or is_holiday(nxt):
            cur = nxt
            continue
        break
    return cur

def monthly_billing_event(year: int, month: int) -> Event:
    fifth = date(year, month, 5)
    next_day = fifth + timedelta(days=1)
    if not is_business_day(fifth):
        final_day = end_of_nonbusiness_period(fifth)
        dt = datetime.combine(final_day, time(14, 0))
    else:
        if is_business_day(next_day):
            dt = datetime.combine(fifth, time(17, 0))
        else:
            final_day = end_of_nonbusiness_period(next_day)
            dt = datetime.combine(final_day, time(14, 0))
    return Event(time=dt, message="월 청구확정 시작!")

def auto_billing1_event(year: int, month: int) -> Event:
    base = date(year, month, 17)
    day1 = previous_business_day(base)
    day2 = day1 - timedelta(days=1)
    alert_time = time(17, 0) if is_business_day(day2) else time(14, 0)
    dt = datetime.combine(day2, alert_time)
    return Event(time=dt, message="자동이체 1차 청구확정 시작!")

def credit_card_event(year: int, month: int) -> Event:
    base = date(year, month, 25)
    if is_business_day(base):
        dt = datetime.combine(base, time(9, 30))
    else:
        nxt = next_business_day(base)
        dt = datetime.combine(nxt, time(9, 30))
    return Event(time=dt, message="신용카드 청구확정 작업 시작!")

def auto_billing2_event(year: int, month: int) -> Event:
    base = date(year, month, 25)
    day1 = previous_business_day(base)
    day2 = day1 - timedelta(days=1)
    alert_time = time(17, 0) if is_business_day(day2) else time(14, 0)
    dt = datetime.combine(day2, alert_time)
    return Event(time=dt, message="자동이체 2차 청구확정 시작!")

def generate_month_events(year: int, month: int):
    return [
        monthly_billing_event(year, month),
        auto_billing1_event(year, month),
        credit_card_event(year, month),
        auto_billing2_event(year, month),
    ]

def load_events(months_ahead: int = 12):
    today = date.today()
    events = []
    for i in range(months_ahead):
        m_year = today.year + ((today.month - 1 + i) // 12)
        m_month = ((today.month - 1 + i) % 12) + 1
        events.extend(generate_month_events(m_year, m_month))
    events.sort(key=lambda e: e.time)
    return events

def main():
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    notifier = TelegramNotifier(token, chat_id)
    events = load_events()
    while True:
        now = datetime.now()
        for e in events:
            if not e.sent and now >= e.time:
                notifier.send_message(e.message)
                e.sent = True
        time_module.sleep(60)

if __name__ == "__main__":
    main()
