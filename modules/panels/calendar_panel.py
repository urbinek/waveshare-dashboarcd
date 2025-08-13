import logging
import textwrap
import datetime
from modules import drawing_utils

def draw_panel(draw, calendar_data, fonts, box_info):
    """Rysuje siatkę kalendarza."""
    logging.debug(f"Rysowanie panelu kalendarza w obszarze: {box_info['rect']}")
    rect = box_info['rect']

    # Zastosowanie globalnego przesunięcia o -50px w górę
    y_offset = box_info.get('y_offset', 0) - 50

    # --- Stałe i Ustawienia Layoutu ---
    cell_width = 48
    cell_height = 40
    grid_width = 7 * cell_width
    font_cal_header = fonts.get('small_bold')
    font_cal_day = fonts.get('small')

    # --- Przygotowanie siatki kalendarza ---
    month_grid = calendar_data.get('month_calendar', [])
    grid_height = (len(month_grid) + 1) * cell_height if month_grid else 0

    # --- Wyśrodkowanie pionowe siatki ---
    box_width = rect[2] - rect[0]
    box_height = rect[3] - rect[1]

    grid_x_start = rect[0] + (box_width - grid_width) // 2
    grid_y_start = rect[1] + (box_height - grid_height) // 2 + y_offset

    # --- Rysowanie Nagłówków Dni Tygodnia ---
    days_of_week = ["Pn", "Wt", "Śr", "Cz", "Pt", "So", "Nd"]
    if month_grid:
        header_center_y = grid_y_start + cell_height // 2
        for i, day_name in enumerate(days_of_week):
            x = grid_x_start + (i * cell_width) + (cell_width // 2)
            draw.text((x, header_center_y), day_name, font=font_cal_header, fill=drawing_utils.BLACK, anchor="mm")

        # Draw underline for header
        line_y = grid_y_start + cell_height
        draw.line([(grid_x_start, line_y), (grid_x_start + grid_width, line_y)], fill=drawing_utils.BLACK, width=1)

    # --- Rysowanie Siatki Kalendarza ---
    if month_grid:
        grid_body_y_start = grid_y_start + cell_height
        for week_idx, week in enumerate(month_grid):
            for day_idx, day_info in enumerate(week):
                day_str = str(day_info.get('day', ''))
                cell_x = grid_x_start + (day_idx * cell_width)
                cell_y = grid_body_y_start + (week_idx * cell_height)

                is_today = day_info.get('is_today', False)
                is_holiday = day_info.get('is_holiday', False)
                day_date_str = day_info.get('date')

                text_x = cell_x + cell_width // 2
                text_y = cell_y + cell_height // 2
                current_font = fonts['small_bold'] if is_today else font_cal_day

                if day_info.get('is_current_month'):
                    text_color = drawing_utils.BLACK # Default color
                    
                    if is_holiday:
                        text_color = drawing_utils.DARK_GRAY # Holiday
                    elif day_date_str:
                        day_date = datetime.date.fromisoformat(day_date_str)
                        if day_date < datetime.date.today():
                            text_color = drawing_utils.LIGHT_GRAY # Past day

                    draw.text((text_x, text_y), day_str, font=current_font, fill=text_color, anchor="mm")

                if is_today:
                    text_bbox = draw.textbbox((text_x, text_y), day_str, font=current_font, anchor="mm")
                    underline_y = text_bbox[3] + 2
                    draw.line([(text_bbox[0], underline_y), (text_bbox[2], underline_y)], fill=drawing_utils.BLACK, width=2)
