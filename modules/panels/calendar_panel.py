import logging
import textwrap

def draw_panel(draw_black, draw_red, calendar_data, fonts, box_info):
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
            draw_black.text((x, header_center_y), day_name, font=font_cal_header, fill=0, anchor="mm")

    # --- Rysowanie Siatki Kalendarza ---
    if month_grid:
        grid_body_y_start = grid_y_start + cell_height
        for week_idx, week in enumerate(month_grid):
            for day_idx, day_info in enumerate(week):
                if not day_info.get('is_current_month'):
                    continue

                day_str = str(day_info.get('day', ''))
                cell_x = grid_x_start + (day_idx * cell_width)
                cell_y = grid_body_y_start + (week_idx * cell_height)

                is_special_day = day_info.get('is_weekend') or day_info.get('is_holiday')
                has_event = day_info.get('has_event')
                is_today = day_info.get('is_today', False)

                text_x = cell_x + cell_width // 2
                text_y = cell_y + cell_height // 2
                current_font = fonts['small_bold'] if is_today else font_cal_day

                if has_event:
                    draw_obj = draw_red if is_special_day else draw_black
                    draw_obj.rectangle((cell_x, cell_y, cell_x + cell_width, cell_y + cell_height), fill=0)
                    draw_obj.text((text_x, text_y), day_str, font=current_font, fill=255, anchor="mm")
                else:
                    draw_obj = draw_red if is_special_day else draw_black
                    draw_obj.text((text_x, text_y), day_str, font=current_font, fill=0, anchor="mm")

                    if is_today:
                        text_bbox = draw_black.textbbox((text_x, text_y), day_str, font=current_font, anchor="mm")
                        underline_y = text_bbox[3] + 2
                        draw_obj.line([(text_bbox[0], underline_y), (text_bbox[2], underline_y)], fill=0, width=2)
