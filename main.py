import requests


class backup:
    def __init__(self, y_disk_token: str, vk_token: str):
        self._y_disk_token = y_disk_token
        self.y_disk_main_url = 'https://cloud-api.yandex.net/v1/disk/'  # f
        self.y_disk_headers = {
            'Authorization': self._y_disk_token
        }
        self._vk_token = vk_token
        self.main_vk_url = 'https://api.vk.com/method/'
        self.main_vk_params = {
            'access_token': self._vk_token,
            'v': '5.21'
        }
        self.new_log = []
        self._set_default_user_info()

    def __del__(self):
        self._update_log_file()

    def __str__(self):
        if self.id is not None:
            return f'{self.first_name} {self.last_name}: https://vk.com/{self.domain}'
        else:
            return f'Пользователь не загружен'

    def start(self, user_id: str):
        """
        Запускает процесс копирования фотографий.
        :param user_id: id или screen_name пользователя
        :return:
        """
        self._user_info_load(user_id)
        if self.id is not None:
            print(f'Выбран пользователь {self}')
            print(f'Загрузить фото из всех альбомов, или только фото профиля?\n'
                  f'\ta - все\n'
                  f'\tp - только профиля\n'
                  f'\tx - отмена загрузки')
            while True:
                input_key = input('>> ')
                if input_key == 'a':
                    albums = self._get_user_albums()
                    break
                elif input_key == 'p':
                    albums = self._get_user_albums(False)
                    break
                elif input_key == 'x':
                    return 0
                else:
                    print(f'Неизвестная команда {input_key}')
            self._upload_photos_to_disk(albums)

    def _update_log_file(self):
        """
        Обновляет log файл
        """
        import time
        import json
        if len(self.new_log) > 0:
            try:
                with open('files/log.json') as f:
                    log_file = json.load(f)
            except FileNotFoundError:
                log_file = {'error': 'file not found'}
                print('log файл не найден при загрузке')
            except PermissionError:
                log_file = {'error': 'file doesn\'t open'}
                print('Не удалось открыть log файл при загрузке')
            if 'error' not in log_file:
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

    def _upload_photos_to_disk(self, albums: list):
        """
        Загружает список альбомов на Яндек.Диск.
        :param albums: список альбомов
            Стуктура списка альбомов:
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
        import time

        if len(albums) > 0:
            url = f'{self.y_disk_main_url}resources'
            params = {'path': '/vk_backups/'}
            requests.put(url, params=params, headers=self.y_disk_headers)
            params['path'] = f'/vk_backups/{self.domain}/'
            requests.put(url, params=params, headers=self.y_disk_headers)
            main_path = params['path']
            response = requests.get(url, params=params, headers=self.y_disk_headers)
            status_code = response.status_code
            if status_code // 100 == 2:
                for album in albums:
                    path_to_album = f'{main_path}{album["title"]}/'
                    params['path'] = path_to_album
                    url = f'{self.y_disk_main_url}resources'
                    requests.put(url, params=params, headers=self.y_disk_headers)
                    response = requests.get(url, params=params, headers=self.y_disk_headers)
                    status_code = response.status_code
                    if status_code // 100 == 2:
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
                                photo_name = str(photo['likes'])
                                photo_format = photo['url'][photo['url'].rfind('.'):]
                                if f'{photo_name}{photo_format}' in files_names:
                                    photo_time = time.gmtime(photo["data"])
                                    photo_date = f'{photo_time.tm_mday}.{photo_time.tm_mon}.{photo_time.tm_year}_in_' \
                                                 f'{photo_time.tm_hour}_hour_{photo_time.tm_min}_min_' \
                                                 f'{photo_time.tm_sec}sec'
                                    photo_name = f'{photo_name}_{photo_date}{photo_format}'
                                    photo_name = photo_name.replace(' ', '_')
                                else:
                                    photo_name = f'{photo_name}{photo_format}'
                                path_to_file = f'{path_to_album}{photo_name}'
                                print(f'\t{photo_name}'.ljust(50), 'загрузка', end='')
                                url = f'{self.y_disk_main_url}resources/upload'
                                params = {
                                    'path': path_to_file,
                                    'url': photo['url']
                                }
                                upload_response = requests.post(url, params=params, headers=self.y_disk_headers)
                                upload_status_code = upload_response.status_code
                                if upload_status_code // 100 == 2:
                                    print(' - успешно')
                                    self.new_log.append({
                                        "file_name": photo_name,
                                        "size": photo['type'],
                                        "album": photo['album_id'],
                                        "user_id": self.id,
                                        "data": time.ctime(time.time())
                                    })
                                    files_names.append(photo_name)
                                else:
                                    print(f'не удачно {upload_status_code}')
                    else:
                        self._y_disk_error(status_code, response.json(), 'создание дериктории альбома')
                    print()
                self._update_log_file()
                print(f'Загрузка фото пользователя {self.first_name} {self.last_name} завершена')
            else:
                self._y_disk_error(status_code, response.json(), 'создание дериктории пользователя')

    def _set_default_user_info(self):
        """
        Установка всех полей, которые содержат информацию о пользователе на значения по умолчанию.
        """
        self.id = None
        self.first_name = ''
        self.last_name = ''
        self.domain = ''

    def _user_info_load(self, user_id: str):
        """
        Загрузка информации о пользователе.
        :param user_id: id или screen_name пользователя
        :return:
        """
        url = f'{self.main_vk_url}users.get'
        params = {**self.main_vk_params, **{'user_ids': user_id, 'fields': 'domain'}}
        response = requests.get(url, params=params)
        status_code = response.status_code
        if status_code // 100 == 2:
            response = response.json()
            try:
                user_info = response['response'][0]
                self.id = user_info['id']
                self.first_name = user_info['first_name']
                self.last_name = user_info['last_name']
                self.domain = user_info['domain']
            except KeyError:
                self._set_default_user_info()
                self._vk_response_error(response, user_id)
        else:
            self._requests_error(status_code, url, params)

    def _get_users_photos(self, count: int = 5, album_id: str = 'profile'):
        """
        Возвращает список фото
        :param count: максимальное колличество получаемых фото
        :param album_id: id альбома, фотографии которого необходимо получить
        :return: списо фото альбома с id == album_id
        Структура списка фото
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
        def photo_max_size_key(photo_info: dict):
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

        users_photos = []
        if self.id is not None:
            url = f'{self.main_vk_url}photos.get'
            params = {
                **self.main_vk_params,
                **{
                    'owner_id': self.id,
                    'album_id': album_id,
                    'extended': '1',
                    'photo_sizes': '1',
                    'count': count
                }
            }
            response = requests.get(url, params=params)
            status_code = response.status_code
            response = response.json()
            if status_code // 100 == 2:
                try:
                    for photo in response['response']['items']:
                        photo_max_size_info = max(photo['sizes'], key=photo_max_size_key)
                        users_photos.append({
                            'url': photo_max_size_info['src'],
                            'type': photo_max_size_info['type'],
                            'data': photo['date'],
                            'likes': photo['likes']['count'],
                            'album_id': photo['album_id']
                        })
                except KeyError:
                    self._vk_response_error(response, self.id)
            else:
                self._requests_error(status_code, url, params)
        else:
            self._vk_user_ist_load()
        return users_photos

    def _get_user_albums(self, is_all_albums: bool = True):
        """
        Возвращает список альбомов пользователя
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
        users_albums = []
        if self.id is not None:
            print('Загрузка информации о альбомах')
            url = f'{self.main_vk_url}photos.getAlbums'
            params = {
                **self.main_vk_params,
                **{'owner_id': self.id, 'need_system': 1}
            }
            response = requests.get(url, params=params)
            status_code = response.status_code
            response = response.json()
            if status_code // 100 == 2:
                try:
                    for album in response['response']['items']:
                        if is_all_albums or album['id'] == -6:
                            users_albums.append({
                                'album_id': album['id'],
                                'title': album['title'],
                                'photos': []
                            })

                except KeyError:
                    self._vk_response_error(response, self.id)
                else:
                    for index, album in enumerate(users_albums):
                        users_albums[index]['photos'] = self._get_users_photos(500, album['album_id'])
            else:
                self._requests_error(status_code, url, params)
        else:
            self._vk_user_ist_load()
        return users_albums

    @staticmethod
    def _y_disk_error(status_code: int, response: dict, action: str):
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

    @staticmethod
    def _vk_user_ist_load():
        """
        Ошибка, пользователь не был загружен
        :return:
        """
        print('Ошибка: Пользователь VK не загружен')

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
