import unicodedata

from apps.assets.folding import FOLD_SOURCE, FOLD_TARGET, fold_for_search
from apps.assets.models import Asset

# Letras que la tabla no pliega: siguen igual en Python y en la base de datos
OUTSIDE_THE_TABLE = ["Ł", "ß", "ж", "α", "ñ", "Č"]
# Alfabetos latinos básico, de Latin-1 y ampliados A y B: contiene toda la tabla
LATIN_CODE_POINTS = range(0x20, 0x250)
TITLE_REPETITIONS = 3


# El título exige un mínimo de caracteres: se repite la letra, que se pliega sola
def stored_foldings(make_asset, characters):
    Asset.objects.bulk_create(
        [make_asset(title=c * TITLE_REPETITIONS) for c in characters]
    )
    return {
        title[0]: folded[0]
        for title, folded in Asset.objects.values_list("title", "title_folded")
    }


def test_the_fold_source_and_target_have_the_same_length_and_no_repeats():
    assert len(FOLD_SOURCE) == len(FOLD_TARGET)
    assert len(set(FOLD_SOURCE)) == len(FOLD_SOURCE)
    assert unicodedata.normalize("NFC", FOLD_SOURCE) == FOLD_SOURCE


def test_python_and_the_database_fold_every_character_of_the_table_the_same_way(
    db, make_asset
):
    characters = [chr(code_point) for code_point in LATIN_CODE_POINTS]
    assert set(FOLD_SOURCE) <= set(characters)

    in_the_database = stored_foldings(make_asset, characters)

    assert {c: fold_for_search(c) for c in characters} == in_the_database


def test_characters_outside_the_table_stay_the_same_in_python_and_in_the_database(
    db, make_asset
):
    assert all(unicodedata.normalize("NFC", c) == c for c in OUTSIDE_THE_TABLE)

    in_the_database = stored_foldings(make_asset, OUTSIDE_THE_TABLE)

    assert in_the_database == {c: c for c in OUTSIDE_THE_TABLE}
    assert [fold_for_search(c) for c in OUTSIDE_THE_TABLE] == OUTSIDE_THE_TABLE
