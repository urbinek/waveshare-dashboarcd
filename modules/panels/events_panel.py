import logging
import datetime
from dateutil import parser
import textwrap
from PIL import Image # Add Image import

from modules.config_loader import config
from modules import drawing_utils

def draw_panel(image, draw, calendar_data, fonts, box_info):
    """Rysuje listę nadchodzących wydarzeń w zdefiniowanym obszarze (box)."""
    logging.debug(f"Rysowanie panelu wydarzeń w obszarze: {box_info['rect']}")
    rect = box_info['rect']
    y_offset = box_info.get('y_offset', 0)
    x_offset = box_info.get('x_offset', 0) # Add x_offset

    line_height = 30
    time_width = 70
    left_padding = 5
    top_padding = 10

    font_event = fonts.get('small')
    font_date = fonts.get('small_bold', font_event)

    max_events = config['google_calendar']['max_upcoming_events']
    events = calendar_data.get('upcoming_events', [])[:max_events]

    y_start_block = rect[1] + top_padding + y_offset
    x_start = rect[0] + left_padding + x_offset # Use x_offset

    title_text = "Nadchodzące:"
    draw.text((x_start, y_start_block), title_text, font=fonts['small_bold'], fill=drawing_utils.BLACK)
    title_bbox = draw.textbbox((x_start, y_start_block), title_text, font=fonts['small_bold'])
    line_y = title_bbox[3] + 2
    draw.line([(title_bbox[0], line_y), (title_bbox[2], line_y)], fill=drawing_utils.BLACK, width=1)

    if not events:
        draw.text((x_start, y_start_block + line_height), "- Brak wydarzeń -", font=font_event, fill=drawing_utils.BLACK)
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
            y_adjustment = 0
            current_font_event = font_event
            current_font_date = font_date

            if is_today:
                is_weekend = event_dt_obj.weekday() >= 5
                is_holiday = event_dt_obj.date() in holiday_dates_set
                is_special_day = is_weekend or is_holiday
                if is_special_day:
                    y_adjustment = -70
                    current_font_event = fonts.get('small_holiday', font_event)
                    current_font_date = fonts.get('small_bold_holiday', font_date)
                    # Today and special day - use DARK_GRAY background, WHITE text
                    # Draw background on a temporary image and paste it
                    bg_rect = (rect[0], y_slot_top + y_adjustment, rect[2], y_slot_top + line_height + y_adjustment)
                    bg_image = Image.new('L', (bg_rect[2] - bg_rect[0], bg_rect[3] - bg_rect[1]), drawing_utils.DARK_GRAY)
                    image.paste(bg_image, (bg_rect[0], bg_rect[1])) # Paste onto main image
                    text_color = drawing_utils.WHITE
                else:
                    # Today, normal day - use BLACK text, WHITE background (default)
                    text_color = drawing_utils.BLACK
                time_formatted = event_dt_obj.strftime('%H:%M')
            else:
                # Normal event - use BLACK text, WHITE background (default)
                text_color = drawing_utils.BLACK
                time_formatted = event_dt_obj.strftime('%d.%m')

            draw.text((x_start, y_centered + y_adjustment), time_formatted, font=current_font_date, fill=text_color, anchor="lm")

            # Truncate and draw summary with smaller ellipsis
            max_len = 30
            display_summary = textwrap.shorten(summary, width=max_len, placeholder="")
            draw.text((x_start + time_width, y_centered + y_adjustment), display_summary, font=current_font_event, fill=text_color, anchor="lm")

            if len(summary) > max_len:
                text_width = draw.textlength(display_summary, font=current_font_event)
                ellipsis_x = x_start + time_width + text_width
                font_ellipsis = fonts.get('ellipsis')
                draw.text((ellipsis_x, y_centered + y_adjustment), "...", font=font_ellipsis, fill=text_color, anchor="lm")

        except (ValueError, TypeError) as e:
            logging.warning(f"Nie udało się przetworzyć daty wydarzenia '{start_str}': {e}")