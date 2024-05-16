import json
import sqlite3
import sys
import time

# ----------------------------------------------------------------------------------------------
# Запрос к пользователю на выполнение скрипта
# ----------------------------------------------------------------------------------------------


def ask_user():
    print("Вы уверены, что хотите пересоздать базу данных? (Y/n) ", end='')
    answer = input().lower()
    while answer not in ['y', 'n']:
        answer = input("Пожалуйста, введите 'Y' или 'N': ").lower()
    return answer == 'y'


if ask_user():
    print("Пересоздание базы данных... Для подтверждения операции нажмите Enter, для отмены - Escape")
    try:
        while True:
            input_key = input()
            if input_key == '':  # Enter
                print("Была нажата клавиша Enter. Выполняется операция...\n")
                time.sleep(2)
                break
            elif input_key.lower() == 'esc':
                print("Была нажата клавиша Escape. Операция отменена.")
                sys.exit(0)
    except KeyboardInterrupt:
        print("Вы нажали Ctrl+C. Операция отменена.")
        sys.exit(0)
else:
    print("Операция отменена.")
    sys.exit(0)


# ----------------------------------------------------------------------------------------------
# Выполнение скрипта
# ----------------------------------------------------------------------------------------------

# Устанавливаем соединение с базой данных
connection = sqlite3.connect('db/data.db')
cursor = connection.cursor()


# ------------------------------------------------------
# Удаление всех данных из БД
# ------------------------------------------------------

cursor.execute('drop table if exists cv_material_class')
cursor.execute('drop table if exists cv_activity_class')
cursor.execute('drop table if exists cv_activity')
cursor.execute('drop table if exists cv_activity_mat')

print('Все таблицы и данные удалены\n')

# ------------------------------------------------------
# Системные таблицы
# ------------------------------------------------------

# ------------------------------------------------------
# Справочники классов
# ------------------------------------------------------

# Таблица cv_material_class
cursor.execute('''
CREATE TABLE IF NOT EXISTS cv_material_class (
    id integer not null primary key,
	name text not null,
	description text
)
''')
print('Таблица cv_material_class создана')

# Таблица cv_activity_class
cursor.execute('''
CREATE TABLE IF NOT EXISTS cv_activity_class (
    id integer not null primary key,
	name text not null,
	description text
)
''')
print('Таблица cv_activity_class создана')


# ------------------------------------------------------
# Activity
# ------------------------------------------------------

# Таблица cv_activity
cursor.execute('''
CREATE TABLE IF NOT EXISTS cv_activity (
    id integer not null primary key,
    class_id integer not null,
	scrs_timestamp text not null,
	scrs_path text not null,
	is_complete boolean,
	result_conf float,
	result_json text,
	speed_ms integer,
	comment text,
	constraint cvact_class_fk foreign key (class_id) references cv_activity_class(id)
)
''')
print('Таблица cv_activity создана')

# ------------------------------------------------------
# Activity material
# ------------------------------------------------------

# Таблица cv_activity_mat
cursor.execute('''
CREATE TABLE IF NOT EXISTS cv_activity_mat (
    id integer not null primary key,
    act_id integer not null,
    mat_class_id integer not null,
	coords text not null,
	conf float,
	comment text,
	constraint cvactmat_act_fk foreign key (act_id) references cv_activity(id),
	constraint cvactmat_matcls_fk foreign key (mat_class_id) references cv_material_class(id)
)
''')
print('Таблица cv_activity_mat создана')


# ------------------------------------------------------
# Данные для базовых справочников
# ------------------------------------------------------
print()

cursor.execute("INSERT INTO cv_activity_class (id, name, description) VALUES (0, 'Скриншот', 'Выполнение скриншота с изображения из видеопотока')")
cursor.execute("INSERT INTO cv_material_class (id, name, description) VALUES (0, 'Модуль', 'Модуль SIM900')")
cursor.execute("INSERT INTO cv_material_class (id, name, description) VALUES (1, 'Антенна', 'Антенна к модулю SIM900')")

print('Справочные данные созданы')
print()

# ------------------------------------------------------
# Создание индексов
# ------------------------------------------------------
# TODO

# ------------------------------------------------------
# Сохраняем изменения и закрываем соединение
# ------------------------------------------------------

connection.commit()
connection.close()

print('Скрипт выполнен\n')
