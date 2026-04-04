from flask import request, session

SUPPORTED_LANGS = ('it', 'en')

MONTHS = {
    'it': {
        1: 'Gennaio', 2: 'Febbraio', 3: 'Marzo', 4: 'Aprile',
        5: 'Maggio', 6: 'Giugno', 7: 'Luglio', 8: 'Agosto',
        9: 'Settembre', 10: 'Ottobre', 11: 'Novembre', 12: 'Dicembre',
    },
    'en': {
        1: 'January', 2: 'February', 3: 'March', 4: 'April',
        5: 'May', 6: 'June', 7: 'July', 8: 'August',
        9: 'September', 10: 'October', 11: 'November', 12: 'December',
    },
}


STATUS_LABELS = {
    'bozza': ('Bozza', 'Draft'),
    'confermata': ('Confermata', 'Confirmed'),
    'chiusa': ('Chiusa', 'Closed'),
}




def get_lang():
    lang = session.get('lang')
    if lang in SUPPORTED_LANGS:
        return lang

    best = request.accept_languages.best_match(SUPPORTED_LANGS)
    return best or 'it'


def tr(it_text, en_text):
    return en_text if get_lang() == 'en' else it_text


def month_name(month):
    return MONTHS.get(get_lang(), MONTHS['it']).get(month, '')


def month_options():
    return MONTHS.get(get_lang(), MONTHS['it'])


def status_label(status):
    it_text, en_text = STATUS_LABELS.get(status, (status, status))
    return tr(it_text, en_text)


