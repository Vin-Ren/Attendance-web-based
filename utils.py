from datetime import datetime
import i18n

from typing import List

dictUpdater = lambda dbase,dupdt:(lambda base,updater:[base.update(updater), base][-1])(dbase,dupdt)


def time_parser(s:str):
    formats = ['%H:%M', '%H:%M:%S', '%H %M', '%H %M %S', '%M', '%H.%M', '%H.%M.%S']
    for _format in formats:
        try:
            return datetime.strptime(s, _format)
        except ValueError:
            # print(s, _format)
            pass
    return datetime.fromtimestamp(int(s))


def json_serializer(obj):
    '''Json serializer for objects not serializable by json'''
    #Ref: https://stackoverflow.com/questions/11875770/how-to-overcome-datetime-datetime-not-json-serializable
    # This function is expandable if more types were needed to be serialized.
    if isinstance(obj, datetime):
        return obj.isoformat()


def setup_i18n(locale:str='id', locale_path:str='./locale', filename_format:str='{namespace}.{format}', fallback_locale:str='en'):
    # Setup i18n
    i18n.load_path.append(locale_path)
    i18n.set('filename_format', filename_format) # Default: {namespace}.{locale}.{format} Ex: foo.en.yaml
    
    i18n.set('locale', locale)
    i18n.set('fallback', fallback_locale)


def make_box(header:str, entries:List[str], padding:int=3):
    texts = []
    max_text_width = len(max([header]+entries, key=len))
    box_width = max_text_width + 2 + padding
    texts.append( "┌{}┐".format(' {} '.format(header).center(box_width,'─')))
    texts.extend(["│{}│".format(entry.center(box_width, ' ')) for entry in entries])
    texts.append( "└{}┘".format(''.center(box_width, '─')))
    return texts