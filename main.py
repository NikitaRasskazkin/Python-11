import requests
import json
import time


class backup:
    class user:
        def __init__(self, user_info: dict):
            try:
                self.id = user_info['id']
                self.first_name = user_info['first_name']
                self.last_name = user_info['last_name']
                self.domain = user_info['domain']
            except KeyError:
                self.id = None
                self.first_name = '  ---  '
                self.last_name = '  --  '
                self.domain = None

        def __str__(self):
            if self.id is not None:
                return f'{self.first_name} {self.last_name}: https://vk.com/{self.domain}'
            else:
                return f'Пользователь не загружен'

    class y_Disk_Api:
        def __init__(self, token: str, user):
            self.user_info = user
            self._main_url = 'https://cloud-api.yandex.net/v1/disk/'
            self._headers = {
                'Authorization': token
            }
            self.new_log = []

        def __del__(self):
            self._update_log_file()

        def _update_log_file(self):
            """
            Обновляет log файл
            """
            if len(self.new_log) < 1:
                return
            log_file = self._get_log_file()
            log_file['log'].extend(self.new_log)
            log_file['update_data'] = time.ctime(time.time())
            try:
                with open('files/log.json', 'w') as f:
                    json.dump(log_file, f, ensure_ascii=False, indent=4)
            except FileNotFoundError:
                print('log файл не найден при сохранении')
            except PermissionError:
                print('Не удалось открыть log файл при сохранении')
            else:
                self.new_log.clear()

        @staticmethod
        def _get_log_file():
            """
            Возвращает информацию из log файла
            :return:
            {
                "update_data": "дата последнего обновлениея файла",
                "log": [
                    {
                        "file_name": "название фото",
                        "size": "размер фото",
                        "album": id альбома,
                        "user_id": id владельца,
                        "data": "дато создания"
                    }
                ]
            }
            в случее ошибки возвращает
            {'error': 'описание ошибки'}
            """
            log_file = {}
            try:
                with open('files/log.json') as f:
                    log_file = json.load(f)
            except FileNotFoundError:
                log_file = {'error': 'file not found'}
                print('log файл не найден при загрузке')
            except PermissionError:
                log_file = {'error': 'file doesn\'t open'}
                print('Не удалось открыть log файл при загрузке')
            finally:
                return log_file

        @staticmethod
        def _error(status_code: int, response: dict, action: str):
            """
            Ошибка при работе с API Я.Диск
            :param status_code: код ошибки запроса
            :param response: json ответ API
            :param action: описание того, во время чего произошла ошибка
            :return:
            """
            try:
                print(f'Ошибка API Y.Disk {status_code}: {response["message"]}\n'
                      f'Во время {action}')
            except KeyError:
                print(f'Ошибка API Y.Disk {status_code}:\n'
                      f'Во время {action}')

        def create_folder(self, path: str):
            """
            Создаёт папку
            :param path: путь к новой папке
            :return: ответ выполнеого запроса
            """
            url = f'{self._main_url}resources'
            params = {'path': path}
            return requests.put(url, params=params, headers=self._headers)

        def get_folder_info(self, path: str):
            """
            Получает метаинформацию о файле или каталоге
            :param path: путь к файлу или папке
            :return: ответ выполнеого запроса
            """
            url = f'{self._main_url}resources'
            params = {'path': path}
            return requests.get(url, params=params, headers=self._headers)

        def load_album(self, album: dict, path: str):
            """
            Загружает альбом по указанному пути.
            :param album: альбом
            {
                'album_id': <id альбома>,
                'title': <Заголовок альбома>,
                'photos': [
                    {
                        'url': <ссылка на фото>,
                        'type': <размер фото>,
                        'data': <дата публикации>,
                        'likes': <колличаство лайков>,
                        'album_id': <id альбома>
                    }
                ]
            }
            :param path: путь, по которому необходимо загрузить альбом.
            :return:
            """
            response = self.get_folder_info(path)
            if response.status_code // 100 != 2:
                self._error(response.status_code, response.json(), 'загрузки альбома')
                return
            try:
                files_names = [
                    name['name']
                    for name in response.json()['_embedded']['items']
                ]
            except KeyError:
                print(f'Альбом \"{album["title"]}\" не загружен, '
                      f'ошибка при получении списка уже сохранённых фото')
            else:
                print(f'Загрузка фото из альбома: \"{album["title"]}\"')
                print(f'имя фотографии'.center(50), f'статус'.center(24))
                for photo in album['photos']:
                    photo_format = photo['url'][photo['url'].rfind('.'):]
                    photo_name = self._generate_photo_name(photo['likes'], photo["data"], photo_format, files_names)
                    upload_status_cod = self._load_photo(photo, photo_name, path)
                    if upload_status_cod // 100 != 2:
                        print(f'не удачно {upload_status_cod}')
                        return
                    print(' - успешно')
                    self.new_log.append({
                        "file_name": photo_name,
                        "size": photo['type'],
                        "album": photo['album_id'],
                        "user_id": self.user_info.id,
                        "data": time.ctime(time.time())
                    })
                    files_names.append(photo_name)

        def _load_photo(self, photo: dict, photo_name: str, path: str):
            """
            Загружает фото по указанному пути.
            :param photo: информация фотографии
            {
                'url': <ссылка на фото>,
                'type': <размер фото>,
                'data': <дата публикации>,
                'likes': <колличаство лайков>,
                'album_id': <id альбома>
            }
            :param photo_name: имя, которое будет присвоено загруженной фотографии
            :param path: путь, по которому необходимо загрузить фото.
            :return: код выполненного запроса
            """
            photo_path = f'{path}{photo_name}'
            print(f'\t{photo_name}'.ljust(50), 'загрузка', end='')
            url = f'{self._main_url}resources/upload'
            params = {
                'path': photo_path,
                'url': photo['url']
            }
            return requests.post(url, params=params, headers=self._headers).status_code

        @staticmethod
        def _generate_photo_name(likes: int, data: int, photo_format: str, files_names: list):
            """
            Генерирует имя фото
            :param likes: фолличество лайков у фото
            :param data: дата публикации фото
            :param photo_format: формат фото
            :param files_names: список уже сушествующих имён
            :return: сгенерированное имя фото
            """
            photo_name = str(likes)
            if f'{photo_name}{photo_format}' in files_names:
                photo_time = time.gmtime(data)
                photo_date = f'{photo_time.tm_mday}.{photo_time.tm_mon}.{photo_time.tm_year}_in_' \
                             f'{photo_time.tm_hour}_hour_{photo_time.tm_min}_min_' \
                             f'{photo_time.tm_sec}sec'
                photo_name = f'{photo_name}_{photo_date}{photo_format}'
                photo_name = photo_name.replace(' ', '_')
            else:
                photo_name = f'{photo_name}{photo_format}'
            return photo_name

        def upload_photos_to_disk(self, albums: list):
            """
            Загружает список альбомов на Яндек.Диск.
            :param albums: список альбомов
                [
                    {
                        'album_id': <id альбома>,
                        'title': <Заголовок альбома>,
                        'photos': [
                            {
                                'url': <ссылка на фото>,
                                'type': <размер фото>,
                                'data': <дата публикации>,
                                'likes': <колличаство лайков>,
                                'album_id': <id альбома>
                            }
                        ]
                    }
                ]
            :return:
            """
            if len(albums) < 1:
                return
            self.create_folder('/vk_backups/')
            main_path = f'/vk_backups/{self.user_info.domain}/'
            self.create_folder(main_path)
            response = self.get_folder_info(main_path)
            if response.status_code // 100 != 2:
                self._error(response.status_code, response.json(), 'создание дериктории пользователя')
                return
            for album in albums:
                album_path = f'{main_path}{album["title"]}/'
                self.create_folder(album_path)
                self.load_album(album, album_path)
                print()
            self._update_log_file()
            print(f'Загрузка фото пользователя {self.user_info.first_name} {self.user_info.last_name} завершена')

    class vk_Api:
        def __init__(self, token: str):
            self._main_url = 'https://api.vk.com/method/'
            self._main_params = {
                'access_token': token,
                'v': '5.21'
            }

        def get_user_info(self, user_id: str):
            """
            Загрузка информации о пользователе.
            :param user_id: id или screen_name пользователя
            :return:
            {
                'id': id пользователя,
                'first_name': "Имя",
                'last_name': "Фамилия",
                'domain': "домин"
            }
            """
            url = f'{self._main_url}users.get'
            params = {**self._main_params, **{'user_ids': user_id, 'fields': 'domain'}}
            response = requests.get(url, params=params)
            status_code = response.status_code
            if status_code // 100 != 2:
                self._requests_error(status_code, url, params)
                return
            response = response.json()
            try:
                response_user_info = response['response'][0]
                user_info = {
                    'id': response_user_info['id'],
                    'first_name': response_user_info['first_name'],
                    'last_name': response_user_info['last_name'],
                    'domain': response_user_info['domain']
                }
                return user_info
            except KeyError:
                self._vk_response_error(response, user_id)
                return {}

        def get_users_photos(self, user_info, count: int = 5, album_id: str = 'profile'):
            """
            Возвращает список фото
            :param user_info: класс user
            :param count: максимальное колличество получаемых фото
            :param album_id: id альбома, фотографии которого необходимо получить
            :return: списо фото альбома с id == album_id
                [
                    {
                        'url': <ссылка на фото>,
                        'type': <размер фото>,
                        'data': <дата публикации>,
                        'likes': <колличество лайков>,
                        'album_id': <id альбома>
                    }
                ]
            """
            url = f'{self._main_url}photos.get'
            params = {
                **self._main_params,
                **{
                    'owner_id': user_info.id,
                    'album_id': album_id,
                    'extended': '1',
                    'photo_sizes': '1',
                    'count': count
                }
            }
            response = requests.get(url, params=params)
            status_code = response.status_code
            response = response.json()
            if status_code // 100 != 2:
                self._requests_error(status_code, url, params)
                return []
            users_photos = self._get_photo_info(response, user_info)
            return users_photos

        def _get_photo_info(self, response: dict, user_info):
            """
            Извлекает необходимую программе информацию из response
            :param response: json ответ вк API с информацией о фотографиях пользователя
            :param user_info: класс user
            :return:
            {
                'url': 'ссылка на фото',
                'type': 'размер фото',
                'data': дата публикации,
                'likes': колличество лайков,
                'album_id': id альбома
            }
            """
            users_photos = []
            try:
                for photo in response['response']['items']:
                    photo_max_size_info = max(photo['sizes'], key=self._photo_max_size_key)
                    users_photos.append({
                        'url': photo_max_size_info['src'],
                        'type': photo_max_size_info['type'],
                        'data': photo['date'],
                        'likes': photo['likes']['count'],
                        'album_id': photo['album_id']
                    })
            except KeyError:
                self._vk_response_error(response, user_info.id)
            return users_photos

        @staticmethod
        def _photo_max_size_key(photo_info: dict):
            """
            Преобразует размер фото (type) в числовое значение
            :param photo_info: информация о фото
                {
                    'url': <ссылка на фото>,
                    'type': <размер фото>,
                    'data': <дата публикации>,
                    'likes': <колличество лайков>,
                    'album_id': <id альбома>
                }
            :return: числовое значение размера фото (чем больше, тем лучше качество)
            """
            sizes = {
                's': 1,
                'm': 2,
                'x': 3,
                'y': 4,
                'z': 5,
                'w': 6
            }
            try:
                if photo_info['type'] in sizes:
                    size = sizes[photo_info['type']]
                else:
                    size = 0
                return size
            except KeyError:
                print('Ошика при преобразовании типа фото')
                return 0

        def get_user_albums(self, user_info, is_all_albums: bool = True):
            """
            Возвращает список альбомов пользователя
            :param user_info: класс user
            :param is_all_albums: True - все альбомы пользователя, False - загруузить только фото профиля
            :return: список полученных альбомов
            [
                {
                    'album_id': <id альбома>,
                    'title': <Заголовок альбома>,
                    'photos': [
                        {
                            'url': <ссылка на фото>,
                            'type': <размер фото>,
                            'data': <дата публикации>,
                            'likes': <колличаство лайков>,
                            'album_id': <id альбома>
                        }
                    ]
                }
            ]
            """
            print('Загрузка информации о альбомах')
            url = f'{self._main_url}photos.getAlbums'
            params = {
                **self._main_params,
                **{'owner_id': user_info.id, 'need_system': 1}
            }
            response = requests.get(url, params=params)
            status_code = response.status_code
            response = response.json()
            if status_code // 100 != 2:
                self._requests_error(status_code, url, params)
                return []
            users_albums = self._get_album_info(user_info, response, is_all_albums)
            return users_albums

        def _get_album_info(self, user_info, response: dict, is_all_albums: bool):
            """
            Извлекает необходимую программе информацию из response
            :param user_info: класс user
            :param response: json ответ вк API с информацией о альбомах пользователя
            :param is_all_albums: True - все альбомы пользователя, False - загруузить только фото профиля
            :return: список альбомов
            [
                {
                    'album_id': <id альбома>,
                    'title': <Заголовок альбома>,
                    'photos': [
                        {
                            'url': <ссылка на фото>,
                            'type': <размер фото>,
                            'data': <дата публикации>,
                            'likes': <колличаство лайков>,
                            'album_id': <id альбома>
                        }
                    ]
                }
            ]
            """
            users_albums = []
            try:
                for album in response['response']['items']:
                    if is_all_albums or album['id'] == -6:
                        users_albums.append({
                            'album_id': album['id'],
                            'title': album['title'],
                            'photos': []
                        })
            except KeyError:
                self._vk_response_error(response, user_info.id)
                return []
            else:
                for index, album in enumerate(users_albums):
                    users_albums[index]['photos'] = self.get_users_photos(user_info, 500, album['album_id'])
                return users_albums

        @staticmethod
        def _vk_response_error(response: dict, user_id: str):
            """
            Ошибка при работе с API VK.
            :param response: json ответ API
            :param user_id: id пользователя, при работе с которым произошла ошибка
            :return:
            """
            try:
                if response['error']['error_code'] == 113:
                    print(f'Ошибка VK API {response["error"]["error_code"]}: '
                          f'Пользователя {user_id} не существует')
                elif response['error']['error_code'] == 30:
                    print(f'Ошибка VK API {response["error"]["error_code"]}: '
                          f'Аккаунт пользователя {user_id} приватный')
                else:
                    print(f'Ошибка VK API {response["error"]["error_code"]}: {response["error"]["error_msg"]}')
            except KeyError:
                print('Неизвестная ошибка VK API')

        @staticmethod
        def _requests_error(status_code, url: str, params: dict = None, headers: dict = None):
            """
            Ошибка запроса
            :param status_code: код ошибки
            :param url: url запроса
            :param params: параметры запроса
            :param headers: заголовки запроса
            :return:
            """
            print(f'Ошибка: Запрос {url}')
            if params is not None:
                print('с параметрами:')
                for key, value in params.items():
                    print(f'\t{key}: {value}')
            if headers is not None:
                print('и заголовками:')
                for key, value in headers.items():
                    print(f'\t{key}: {value}')
            print(f'завершился с ошибкой: {status_code}')

    def __init__(self, y_disk_token: str, vk_token: str):
        self._y_disk_token = y_disk_token
        self._vk_token = vk_token

    def start(self, user_id: str):
        """
        Запускает процесс копирования фотографий.
        :param user_id: id или screen_name пользователя
        :return:
        """
        vk = self.vk_Api(self._vk_token)
        user_info = self.user(vk.get_user_info(user_id))
        y_disk = self.y_Disk_Api(self._y_disk_token, user_info)
        if user_info.id is None:
            self._user_ist_load()
            return
        print(f'Выбран пользователь {user_info}')
        print(f'Загрузить фото из всех альбомов, или только фото профиля?\n'
              f'\ta - все\n'
              f'\tp - только профиля\n'
              f'\tx - отмена загрузки')
        while True:
            input_key = input('>> ')
            if input_key == 'a':
                albums = vk.get_user_albums(user_info)
                break
            elif input_key == 'p':
                albums = vk.get_user_albums(user_info, False)
                break
            elif input_key == 'x':
                return 0
            else:
                print(f'Неизвестная команда {input_key}')
        y_disk.upload_photos_to_disk(albums)

    @staticmethod
    def _user_ist_load():
        """
        Ошибка, пользователь не был загружен
        :return:
        """
        print('Ошибка: Пользователь VK не загружен')


def main():
    y_disk_token = ''
    vk_token = ''
    backup_photos = backup(y_disk_token=y_disk_token, vk_token=vk_token)
    print(f'Добро пожаловать в программу резервного копирования фотографий пользователей Вконтакте\n'
          f'Для просмотра допустимых команд введите help')
    while True:
        command = input('>> ').split()
        if command[0] == 'help':
            print(f'\tx - выход из программы\n'
                  f'\tu <id или screen name пользоватебя> - выбор пользователя\n'
                  f'\thelp - справка')
        elif command[0] == 'x':
            break
        elif command[0] == 'u':
            if len(command) > 1:
                backup_photos.start(command[1])
            else:
                print(f'Ошибка: отсутствует аргумент <id или screen name пользоватебя>')
        else:
            print(f'Недопустимая комманда {command[0]}')
    print(f'Программа завершена')


if __name__ == '__main__':
    main()
