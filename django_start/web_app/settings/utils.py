from envparse import env


def parse_str_to_list(name: str, default: list[str]| str| None = None,
                      separator: str| None = ',') -> list[str]:
    """
    Преобразование строки в список
    :param name: имя переменной окружения
    :param default: значение по умолчанию
    :param separator: разделитель
    :return:
    """
    if default and isinstance(default, str):
        default = [default]

    data = env.str(name, default=None)
    return [v for v in data.split(separator) if v] if data else default
