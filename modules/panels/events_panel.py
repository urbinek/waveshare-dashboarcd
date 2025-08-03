import logging
import datetime
from dateutil import parser
import textwrap

from modules.config_loader import config

def draw_panel(draw_black, draw_red, calendar_data, fonts, box_info):
    """Rysuje listę nadchodzących wydarzeń w zdefiniowanym obszarze (box)."""
    logging.debug(f"Rysowanie panelu wydarzeń w obszarze: {box_info['rect']}")
    rect = box_info['rect']
    y_offset = box_info.get('y_offset', 0)

    line_height = 30
    time_width = 70
    left_padding = 20
    top_padding = 15

    font_event = fonts.get('small')
    font_date = fonts.get('small_bold', font_event)

    max_events = config['google_calendar']['max_upcoming_events']
    events = calendar_data.get('upcoming_events', [])[:max_events]

    y_start_block = rect[1] + top_padding + y_offset
    x_start = rect[0] + left_padding

    draw_black.text((x_start, y_start_block), "Nadchodzące:", font=fonts['small_bold'], fill=0)

    if not events:
        draw_black.text((x_start, y_start_block + line_height), "- Brak wydarzeń -", font=font_event, fill=0)
        return

    today = datetime.date.today()
    holiday_dates_set = {datetime.date.fromisoformat(d) for d in calendar_data.get('holiday_dates', [])}

    for i, event in enumerate(events):
        y_slot_top = y_start_block + ((i + 1) * line_height)
        y_centered = y_slot_top + (line_height // 2)

        start_str = event.get('start')
        if not start_str:
            continue

        try:
            event_dt_obj = parser.isoparse(start_str)
            is_today = event_dt_obj.date() == today
            summary = event.get('summary', 'Brak tytułu')
            truncated_summary = textwrap.shorten(summary, width=30, placeholder="...")

            if event.get('is_holiday'):
                draw_obj = draw_red
                text_fill = 255
                time_formatted = event_dt_obj.strftime('%d.%m')
                draw_obj.rectangle((rect[0], y_slot_top, rect[2], y_slot_top + line_height), fill=0)
            elif is_today:
                is_weekend = event_dt_obj.weekday() >= 5
                is_holiday = event_dt_obj.date() in holiday_dates_set
                is_special_day = is_weekend or is_holiday
                draw_obj = draw_red if is_special_day else draw_black
                text_fill = 255
                time_formatted = event_dt_obj.strftime('%H:%M')
                draw_obj.rectangle((rect[0], y_slot_top, rect[2], y_slot_top + line_height), fill=0)
            else:
                draw_obj = draw_black
                text_fill = 0
                time_formatted = event_dt_obj.strftime('%d.%m')

            draw_obj.text((x_start, y_centered), time_formatted, font=font_date, fill=text_fill, anchor="lm")
            draw_obj.text((x_start + time_width, y_centered), truncated_summary, font=font_event, fill=text_fill, anchor="lm")
        except (ValueError, TypeError) as e:
            logging.warning(f"Nie udało się przetworzyć daty wydarzenia '{start_str}': {e}")