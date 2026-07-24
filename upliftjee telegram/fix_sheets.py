with open('/root/upliftjee/sheets.py', 'r') as f:
    content = f.read()

# 1. Update save_student function signature
old_sig = "def save_student(user_id, name, username, message, score, member_status, history):"
new_sig = "def save_student(user_id, name, username, message, score, member_status, history, preferred_language=None, first_dm_sent=None):"
content = content.replace(old_sig, new_sig)

# 2. Update the row_index branch (existing user) - add K and L columns
old_update = '''            if row_index:
                old_hot = existing_row[9] if len(existing_row) > 9 else "NO"
                final_hot = "YES" if is_hot == "YES" or old_hot == "YES" else "NO"

                sheet.batch_update([
                    {"range": f"E{row_index}", "values": [[message]]},
                    {"range": f"F{row_index}", "values": [[str(final_score)]]},
                    {"range": f"G{row_index}", "values": [[member_status]]},
                    {"range": f"H{row_index}", "values": [[datetime.now().strftime("%d/%m/%Y %H:%M")]]},
                    {"range": f"I{row_index}", "values": [[history_to_save]]},
                    {"range": f"J{row_index}", "values": [[final_hot]]},
                ])'''

new_update = '''            if row_index:
                old_hot = existing_row[9] if len(existing_row) > 9 else "NO"
                final_hot = "YES" if is_hot == "YES" or old_hot == "YES" else "NO"

                old_lang = existing_row[10] if len(existing_row) > 10 else ""
                final_lang = preferred_language if preferred_language else old_lang

                old_dm_sent = existing_row[11] if len(existing_row) > 11 else "NO"
                final_dm_sent = first_dm_sent if first_dm_sent else old_dm_sent

                sheet.batch_update([
                    {"range": f"E{row_index}", "values": [[message]]},
                    {"range": f"F{row_index}", "values": [[str(final_score)]]},
                    {"range": f"G{row_index}", "values": [[member_status]]},
                    {"range": f"H{row_index}", "values": [[datetime.now().strftime("%d/%m/%Y %H:%M")]]},
                    {"range": f"I{row_index}", "values": [[history_to_save]]},
                    {"range": f"J{row_index}", "values": [[final_hot]]},
                    {"range": f"K{row_index}", "values": [[final_lang]]},
                    {"range": f"L{row_index}", "values": [[final_dm_sent]]},
                ])'''

content = content.replace(old_update, new_update)

# 3. Update the append_row branch (new user) - add K and L values
old_append = '''            else:
                sheet.append_row([
                    datetime.now().strftime("%d/%m/%Y %H:%M"),
                    name,
                    str(user_id),
                    username or "",
                    message,
                    str(final_score),
                    member_status,
                    datetime.now().strftime("%d/%m/%Y %H:%M"),
                    history_to_save,
                    is_hot
                ])'''

new_append = '''            else:
                sheet.append_row([
                    datetime.now().strftime("%d/%m/%Y %H:%M"),
                    name,
                    str(user_id),
                    username or "",
                    message,
                    str(final_score),
                    member_status,
                    datetime.now().strftime("%d/%m/%Y %H:%M"),
                    history_to_save,
                    is_hot,
                    preferred_language or "",
                    first_dm_sent or "NO"
                ])'''

content = content.replace(old_append, new_append)

# 4. Add new helper functions at the end of file
new_functions = '''

def get_preferred_language(user_id):
    try:
        sheet = get_sheet()

        def _check():
            all_rows = sheet.get_all_values()
            user_id_str = str(user_id)
            for row in all_rows[1:]:
                if row and row[2] == user_id_str:
                    if len(row) > 10 and row[10]:
                        return row[10]
                    return None
            return None

        return _safe_sheet_call(_check)

    except Exception as e:
        logger.error(f"❌ Get preferred language error: {e}")
        return None


def get_first_dm_sent(user_id):
    try:
        sheet = get_sheet()

        def _check():
            all_rows = sheet.get_all_values()
            user_id_str = str(user_id)
            for row in all_rows[1:]:
                if row and row[2] == user_id_str:
                    if len(row) > 11 and row[11] == "YES":
                        return True
                    return False
            return None  # user doesn't exist in sheet at all

        return _safe_sheet_call(_check)

    except Exception as e:
        logger.error(f"❌ Get first dm sent error: {e}")
        return False
'''

content = content.rstrip() + "\n" + new_functions

with open('/root/upliftjee/sheets.py', 'w') as f:
    f.write(content)

print("sheets.py updated!")
