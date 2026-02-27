from django.db import connection


def sql_counter(func):
    """Декоратор для вывода вызванных запросов в БД"""
    def inner(*args, **kwargs):
        """Функция-обёртка"""
        connection.queries_log.clear()

        res = func(*args, **kwargs)

        total_queries = len(connection.queries)
        for i, query in enumerate(connection.queries, 1):
            print(f'Запрос: {i}')
            print(f'SQL: {query["sql"]}')
            print()
        print(f'Total queries: {total_queries}')
        print()

        return res

    return inner
