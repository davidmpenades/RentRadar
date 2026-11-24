# Misma tabla para la columna de la base de datos y para el texto buscado.
# Cada carácter de origen se cambia por el de destino de su misma posición:
# si el destino fuera más corto, translate borraría caracteres.
FOLD_SOURCE = (
    # Letras latinas básicas
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    # Con tilde, diéresis o cedilla
    "ÀÁÂÃÄÅàáâãäå"
    "Çç"
    "ÈÉÊËèéêë"
    "ÌÍÎÏìíîï"
    "ÒÓÔÕÖòóôõö"
    "ÙÚÛÜùúûü"
    "ÝŸýÿ"
    # La Ñ solo pasa a minúscula: la ñ sigue siendo distinta de la n
    "Ñ"
    # Ligaduras y la Ø solo pasan a minúscula
    "ÆŒØ"
)
FOLD_TARGET = (
    # Letras latinas básicas
    "abcdefghijklmnopqrstuvwxyz"
    # Con tilde, diéresis o cedilla
    "aaaaaaaaaaaa"
    "cc"
    "eeeeeeee"
    "iiiiiiii"
    "oooooooooo"
    "uuuuuuuu"
    "yyyy"
    # La Ñ solo pasa a minúscula: la ñ sigue siendo distinta de la n
    "ñ"
    # Ligaduras y la Ø solo pasan a minúscula
    "æœø"
)

_FOLD_TABLE = str.maketrans(FOLD_SOURCE, FOLD_TARGET)


def fold_for_search(text):
    return text.translate(_FOLD_TABLE)
