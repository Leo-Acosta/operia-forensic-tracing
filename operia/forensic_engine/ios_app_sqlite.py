"""Original bounded Safari table reader; no source paths, joins or epoch guesses."""
import math
import sqlite3

from operia.forensic_engine.contracts import EngineInputError, ReadResult
from operia.forensic_engine.sqlite_readers import preserved_copy, safe_schema, UnsupportedSQLite, WARNINGS

MAX_APP_ROWS = 500
COLUMNS = {
    'history_items': {'id': 'INTEGER', 'url': 'TEXT'},
    'history_visits': {'id': 'INTEGER', 'history_item': 'INTEGER', 'visit_time': 'REAL', 'title': 'TEXT'},
}


def authorize_safari(action, first, second, database, origin):
    if origin is not None or database not in (None, 'main'):
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_SELECT:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_READ and (first in ('sqlite_master', 'sqlite_schema') or
            second in COLUMNS.get(first, {})):
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_PRAGMA and ((first, second) == ('quick_check', None) or
            first == 'table_xinfo' and second in COLUMNS):
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def positive_id(value):
    return type(value) is int and value > 0


def text_value(value, limit):
    return isinstance(value, str) and len(value) <= limit and not any(
        ord(c) < 32 or ord(c) == 127 for c in value)


class SafariHistoryReader:
    identifier = 'operia.ios.safari-history'
    version = '1.0.0'
    platform = 'ios'
    format = 'ios-safari-history-sqlite'
    dependencies = ()

    def read(self, source):
        warnings = WARNINGS + [
            'Perfil Safari estructural, validado solo con muestras sintéticas; no identifica versión iOS ni autentica aplicación/dispositivo.',
            'visit_time es el valor SQLite almacenado; época, unidad y zona no contrastadas. No se genera cronología.',
            'No acredita navegación local, apertura efectiva, comunicación, identidad del usuario ni ausencia de compromiso.',
            'Sin WAL/SHM, borrados, otras aplicaciones, BLOB, perfiles, etiquetas, sincronización, redirecciones ni envío automático a IA.']
        excluded = []
        try:
            with preserved_copy(source.raw, authorizer=authorize_safari) as db:
                objects = safe_schema(db)
                tables = {name for kind, name, _, _ in objects if kind == 'table'}
                if not set(COLUMNS) <= tables:
                    raise UnsupportedSQLite('Perfil requiere tablas ordinarias history_items e history_visits')
                for table, required in COLUMNS.items():
                    columns = db.execute('PRAGMA table_xinfo(' + table + ')').fetchall()
                    actual = {c[1]: c[2].upper() for c in columns}
                    if (not required.items() <= actual.items() or any(c[6] for c in columns)
                            or [(c[1], c[5]) for c in columns if c[5]] != [('id', 1)]):
                        raise UnsupportedSQLite('Variante de columnas o clave primaria Safari fuera del perfil')
                    for c in columns:
                        if c[1] not in required:
                            # Never repeat untrusted column names or their values in exclusions.
                            excluded.append({'locator': table + '/column:' + str(c[0]),
                                             'reason': 'Columna fuera de la selección permitida; contenido no consultado'})
                for kind, name, _, _ in objects:
                    if kind == 'table' and name not in COLUMNS:
                        pointer = name.replace('~', '~0').replace('/', '~1')
                        excluded.append({'locator': 'table/' + pointer, 'reason': 'Tabla fuera de cobertura; filas no consultadas'})
                items = db.execute('SELECT id,url FROM main.history_items ORDER BY id LIMIT 501').fetchall()
                visits = db.execute('SELECT id,history_item,visit_time,title FROM main.history_visits ORDER BY id LIMIT 501').fetchall()
                if len(items) > MAX_APP_ROWS or len(visits) > MAX_APP_ROWS:
                    raise UnsupportedSQLite('Safari supera 500 filas por tabla; sin publicación parcial')
                mapping = {}
                for item_id, url in items:
                    if not positive_id(item_id):
                        raise UnsupportedSQLite('Clave primaria de history_items fuera de perfil')
                    if not text_value(url, 2048) or not url:
                        excluded.append({'locator': 'history_items/id:' + str(item_id), 'reason': 'URL almacenada fuera de límites; valor no publicado'})
                    else:
                        mapping[item_id] = url
                records, referenced = [], set()
                for visit_id, item_id, stamp, title in visits:
                    if not positive_id(visit_id):
                        raise UnsupportedSQLite('Clave primaria de history_visits fuera de perfil')
                    locator = 'history_visits/id:' + str(visit_id)
                    if not positive_id(item_id) or item_id not in mapping:
                        excluded.append({'locator': locator, 'reason': 'Referencia a history_items ausente o fuera de perfil'})
                        continue
                    if ((stamp is not None and (type(stamp) not in (int, float) or not math.isfinite(stamp)))
                            or (title is not None and not text_value(title, 2048))):
                        excluded.append({'locator': locator, 'reason': 'Fecha o título almacenado fuera de límites; fila no publicada'})
                        continue
                    referenced.add(item_id)
                    fields = {'visit_id': visit_id, 'history_item_id': item_id, 'stored_url': mapping[item_id],
                              'stored_title': title, 'stored_visit_time': stamp,
                              'stored_visit_time_type': 'null' if stamp is None else type(stamp).__name__}
                    records.append({'locator': locator, 'kind': 'ios_safari_history_visit',
                                    'original': fields, 'normalized': dict(fields), 'time': None})
                for item_id in sorted(mapping.keys() - referenced):
                    excluded.append({'locator': 'history_items/id:' + str(item_id),
                                     'reason': 'Elemento sin visita interpretable en esta copia; no se infiere borrado'})
                return ReadResult('analizado' if records else 'no_compatible' if excluded else 'sin_registros',
                                  records=records, excluded=excluded, warnings=warnings)
        except UnsupportedSQLite as error:
            return ReadResult('no_compatible', warnings=warnings + [str(error)],
                              excluded=[{'locator': 'database', 'reason': str(error)}])
        except EngineInputError:
            raise
        except (sqlite3.Error, ValueError, UnicodeError, OverflowError, MemoryError):
            return ReadResult('corrupto', warnings=warnings + ['Imagen inválida o presupuesto SQLite excedido'],
                              excluded=[{'locator': 'database', 'reason': 'Sin publicación parcial; bytes originales preservados'}])
