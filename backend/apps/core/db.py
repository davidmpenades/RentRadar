from django.core.exceptions import NON_FIELD_ERRORS
from django.db import IntegrityError, connection, transaction

CONSTRAINT_VIOLATED = "constraint_violated"


def run_guarded(write, constraint_codes):
    violated = None
    try:
        with transaction.atomic():
            result = write()
            check_deferred_constraints()
    except IntegrityError as exc:
        violated = constraint_name(exc)
    # Devuelve códigos para lanzar fuera del except: el IntegrityError lleva el valor
    if violated is None:
        return result, {}
    return None, codes_for_constraint(violated, constraint_codes)


def check_deferred_constraints():
    with connection.cursor() as cursor:
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        # Al terminar bien las deja diferidas, sea cual sea el modo con el que se entró
        cursor.execute("SET CONSTRAINTS ALL DEFERRED")


def constraint_name(error):
    diag = getattr(error.__cause__, "diag", None)
    return getattr(diag, "constraint_name", None) or ""


def codes_for_constraint(name, constraint_codes):
    field, code = constraint_codes.get(name, (NON_FIELD_ERRORS, CONSTRAINT_VIOLATED))
    return {field: [code]}
