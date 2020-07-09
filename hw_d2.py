import requests
import datetime
import copy
import time
import json
from storage_for_acess_token import access_token
import re
import psycopg2


def get_age(birthday):
    today = datetime.date.today()
    age = today.year - birthday.year
    if today.month < birthday.month:
        age -= 1
    elif today.month == birthday.month and today.day < birthday.day:
        age -= 1
    return age


class Users_VK:
    def __init__(self):
        # находим группы пользователя

        # 1)Получаем ID пользователя
        user_id = input('Введите ID пользователя, ник или нажмите Enter, чтобы выбрать себя: ')
        if user_id == '':
            user_id = requests.get('https://api.vk.com/method/users.get',
                                   {'access_token': access_token, 'v': 5.103})
        else:
            user_id = requests.get('https://api.vk.com/method/users.get',
                                   {'access_token': access_token, 'user_ids': user_id, 'v': 5.103})
        self.user_id = user_id.json()['response'][0]['id']

        # Получаем группы:
        groups = requests.get('https://api.vk.com/method/groups.get',
                              {'access_token': access_token, 'user_id': self.user_id, 'v': 5.103})
        try:
            groups_list = (groups.json()['response']['items'])
            self.group_id_for_param = groups_list
        except:
            print("групп не найдено или они закрыты")
            self.group_id_for_param = []

        # находим данные пользователя
        person_data = requests.get('https://api.vk.com/method/users.get',
                                   {'access_token': access_token, 'user_ids': self.user_id, 'v': 5.103,
                                    'fields': 'sex, bdate, city, interests,relation'})
        person_data_2 = (person_data.json()['response'])
        data = copy.copy(person_data_2)
        # День рождения
        try:
            self.person_bday_year = get_age(datetime.datetime.strptime(data[0]['bdate'], '%d.%m.%Y'))
        except:
            self.person_bday_year = int(input('Сколько вам полных лет? '))

        # Пол
        self.person_sex = data[0]['sex']
        if self.person_sex == 1:
            self.search_person_sex = 2
        else:
            self.search_person_sex = 1

        # Интересы
        try:
            if data[0]['interests'] == '':
                interest = input("Укажите свои интересы: ")
                self.insterests_list = re.split(r',| ', interest)
            else:
                self.insterests_list = re.split(r',| ', data[0]['interests'])
        except:
            interest = input("Укажите свои интересы: ")
            self.insterests_list = re.split(r',| ', interest)

        # Город
        try:
            self.person_city = data[0]['city']['id']
        except:
            self.person_city = 1  # из-за отсутствующей базы городов с ID - просто подставляю Москву

        # Семейный статус
        try:
            self.person_relation = data[0]['relation']
        except:
            self.person_relation = 0

    def search_people_with_hints(self):
        people_from_search = requests.get('https://api.vk.com/method/users.search',
                                          {'access_token': access_token, 'v': 5.103, 'count': 20,
                                           'fields': 'bdate, city, interests, relation', 'sex': self.search_person_sex,
                                           'city': self.person_city, 'age_from': self.person_bday_year, 'has_photo': 1,
                                           'age_to': (self.person_bday_year + 1)})
        search_result = (people_from_search.json()['response']['items'])
        return search_result

    def find_same_interests(self, list_people):
        for i in list_people:
            i['match'] = 0
            try:
                for interest_str in self.insterests_list:
                    if re.search(r'%s' % interest_str, i['interests']) and len(interest_str) > 3:
                        i['match'] = i['match'] + 1
            except:
                pass
        return list_people

    def friend_is_member(self, user_ids):
        count_member_group = 0
        for groups_id in self.group_id_for_param:
            time.sleep(0.4)
            groups = requests.get('https://api.vk.com/method/groups.isMember',
                                  {'access_token': access_token, 'v': 5.103, 'group_id': groups_id,
                                   'user_ids': user_ids['id']})
            count_member_group = count_member_group + groups.json()['response'][0]['member']
        user_ids['groups_match'] = count_member_group

    def all_match(self, top_20_list):
        for user in top_20_list:
            match_count = 0
            match_count = match_count + user['groups_match'] * 0.5 + user['match'] * 0.6
            if self.person_sex != self.search_person_sex:
                match_count += 0.5
            try:
                if user['relation'] == 1 or user['relation'] == 6:
                    match_count += 0.5
            except:
                pass
            user['match_count'] = match_count
        return top_20_list

    def get_porfile_pic(self, top_10_list):
        for top_10 in top_10_list:
            time.sleep(0.4)
            profile_pic_list = requests.get('https://api.vk.com/method/photos.get',
                                            {'access_token': access_token, 'v': 5.103, 'album_id': 'profile',
                                             'owner_id': top_10['id'],
                                             'extended': 1})
            top_photo_for_append = []
            try:
                for photo in profile_pic_list.json()['response']['items']:
                    top_photo_for_append.append({'like': photo['likes']['count'], 'url': photo['sizes'][-1]['url']})
                top_photo_for_append = sorted(top_photo_for_append, key=lambda likes: likes['like'], reverse=True)[:3]
                top_10['top3photo'] = top_photo_for_append
            except:
                top_10['top3photo'] = 'Фото нет или не загружается'

    def dump_into_json(self, top_10_list):
        with open("groups.json", "w", encoding="utf-8") as file:
            json.dump(top_10_list, file)

    def check_all_data(self, top_10_list):
        for top_10 in top_10_list:
            try:
                top_10['bdate']
            except:
                top_10['bdate'] = 0

            try:
                top_10['relation']
            except:
                top_10['relation'] = 0

            try:
                top_10['interests']
            except:
                top_10['interests'] = "нет данных"


class DB_Work:
    def __init__(self):
        self.conn = psycopg2.connect(dbname='netology_test', user='netology_user', password='test')
        self.cur = self.conn.cursor()

    def create_db(self):
        self.cur.execute("""
        create table if not exists Users_match(
        id integer not null PRIMARY KEY,
        first_name character varying(200) not null,
        last_name character varying(200) not null,
        bdate character varying(100),
        city character varying(200),
        relation numeric(10,0),
        interests character varying(500),
        match numeric(10,0),
        groups_match numeric(10,0),
        match_count numeric(10,2),
        top3photo character varying(500));
        """)

        self.conn.commit()

    def add_top_10_list(self, top_10_list):
        for top_10 in top_10_list:
            top_10['top3photo'] = list(map(lambda x: json.dumps(x), top_10['top3photo']))
            self.cur.execute(
                "INSERT INTO Users_match (id, first_name, last_name, bdate, city,relation,interests,match,groups_match,match_count,top3photo) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (top_10['id'], top_10['first_name'], top_10['last_name'], top_10['bdate'], top_10['city']['title'],
                 top_10['relation'], top_10['interests'], top_10['match'], top_10['groups_match'],
                 top_10['match_count'], top_10['top3photo']))
            self.conn.commit()

    def get_top_10_list(self):
        self.cur.execute("SELECT * FROM Users_match")
        print(self.cur.fetchall())


def vkinder():
    # 2) Создаем нашего пользователя получачем по нему все данные

    new_user = Users_VK()

    # 4) Находим список людей и сравниваем их интересы со своими (Количество совпадений вписываем в дополнительный эллементы словаря "match"

    list_for_sort = new_user.find_same_interests(new_user.search_people_with_hints())

    top_20_list = list_for_sort

    # 7) Находим количество совпадений групп с пользователем
    count_for_list = 0
    print('проверяем количество вхождений людей из поиска с группами пользователя')
    for user in top_20_list:
        time.sleep(0.5)
        count_for_list += 1
        print(f'Выполнено {count_for_list} запросов из {len(top_20_list)}')
        new_user.friend_is_member(user)

    # 8) Подсчитываем совпадения по нескольким полям и получаем match_count

    top_20_list = new_user.all_match(top_20_list)

    # 9) Сортируем по количеству набранных балов

    top_20_list = sorted(top_20_list, key=lambda key: key['match_count'], reverse=True)

    # 10) Отбираем первые 10 аккаунтов в отсортированном списке

    top_10_list = top_20_list[:10]

    # 11) ищем профильные фотографии/ внутри сортируем по количеству лайков и оставляем первые 3

    new_user.get_porfile_pic(top_10_list)
    new_user.check_all_data(top_10_list)

    # 12) Выгружаем в json

    new_user.dump_into_json(top_10_list)
    print('данные выгружены в файл json')

    # 13) Записываем в базу

    work_with_base = DB_Work()
    work_with_base.create_db()
    work_with_base.add_top_10_list(top_10_list)
    print('данные выгружены в БД')
    work_with_base.get_top_10_list()
    work_with_base.conn.close()


vkinder()
