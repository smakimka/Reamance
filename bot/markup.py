from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


class Markup:
    def __init__(self, body, positional_callback=True):
        self.reply = self._form_reply(body)
        self.inline = self._form_inline(body, positional_callback=positional_callback)

    def _form_inline(self, body, positional_callback):
        inline_markup = []
        for row_num, row in enumerate(body):
            inline_markup.append([])
            for cell_num, cell in enumerate(row):
                inline_markup[row_num].append(
                    InlineKeyboardButton(cell,
                                         callback_data=f'{row_num}:{cell_num}' if positional_callback else cell)
                )

        return InlineKeyboardMarkup(inline_markup)

    def _form_reply(self, body):
        return ReplyKeyboardMarkup(body, resize_keyboard=True)

    def add_callback(self, row, col, callback):
        self.inline.inline_keyboard[row][col].callback_data = callback
