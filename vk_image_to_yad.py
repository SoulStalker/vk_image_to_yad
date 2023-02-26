import json
import requests


class VkApiClient:
    def __init__(self, token: str, api_version: str, user_ids: str, base_url: str = "https://api.vk.com"):
        self.user_ids = user_ids
        self.token = token
        self.api_version = api_version
        self.base_url = base_url

    def general_params(self):
        return {
            'access_token': self.token,
            'v': self.api_version,
        }

    def get_photos(self, album_id='profile', extended=1, photo_sizes=1):
        """
        Метод получает список фотографий по выбранному альбому
        :param
        album_id:
            wall — фотографии со стены,
            profile — фотографии профиля,
            saved — сохраненные фотографии. Возвращается только с ключом доступа пользователя.
        extended=1 возвращаются дополнительные поля:
            likes — количество отметок Мне нравится и информация о том, поставил ли лайк текущий пользователь,
            comments — количество комментариев к фотографии,
            tags — количество отметок на фотографии,
            can_comment — может ли текущий пользователь комментировать фото (1 — может, 0 — не может),
            reposts — число репостов фотографии.
        """
        params = {
            'owner_id': self.user_ids,
            'album_id': album_id,
            'extended': extended,
            'photo_sizes': photo_sizes
        }
        response = requests.get(f'{self.base_url}/method/photos.get',
                                params={**params, **self.general_params()})
        check = response.json()
        if 'error' in check.keys():
            print('Ошибка:', check['error']['error_msg'])
        else:
            return response.json()


class YaUploader:
    def __init__(self, token: str, qty: int = 5):
        self.dir_name = None
        self.token = token
        self.quantity = qty
        self.upload_url = 'https://cloud-api.yandex.net/v1/disk/resources/'
        self.auth_headers = {"Authorization": f"OAuth {ya_token}"}

    def create_dir(self, directory: str):
        """
        Метод создает папку на Яндекс диске
        """
        params = {'path': directory}
        response = requests.put(self.upload_url, headers=self.auth_headers, params=params)
        if response.status_code == 201:
            print(f'Папка {directory} успешно создана')
        elif response.status_code == 409:
            print(f'Папка {directory} уже существует')
        else:
            print(f'Неизвестная ошибка. Код ошибки: {response.status_code}')

    def post_file(self, name, directory, url):
        """
        Метод загружает файлы на Яндекс Диск по ссылке из интернета
        """
        params = {'path': f'/{directory}/{name}', 'url': url}
        res = requests.post(self.upload_url + "upload", headers=self.auth_headers, params=params)
        if res.status_code == 202:
            print(f'Файл {name} успешно загружен в папку {directory}!')


def get_biggest_photo(photos_list: list) -> dict:
    """
    Выбираем фото наибольшего размера (ширина/высота в пикселях)
    некоторые старые фото имеют размер 0х0 такие фото возьмем по типу х
    """
    if sum([item['height'] + item['width'] for item in photos_list]) == 0:
        inter = list(filter(lambda x: x['type'] == 'x', photos_list))[0]
        size = f"{inter['width']}x{inter['height']}"
        return {'size': size, 'url': inter['url']}
    else:
        inter = (max(photos_list, key=lambda x: x['width'] + x['height']))
        size = f"{inter['width']}x{inter['height']}"
        return {'size': size, 'url': inter['url']}


def upload_photos_to_yad(files_list: list, token, directory):
    """
    Загружаем фото на яндекс диск по списку файлов
    """
    uploader = YaUploader(token)
    uploader.create_dir(directory)
    try:
        for photo_obj in files_list:
            uploader.post_file(photo_obj['filename'], directory=directory, url=photo_obj['url'])
        print('-' * 15)
        print('Загрузка завершена')
    except TypeError:
        print()


def get_vk_photos(user_id: str, token: str, album: str, qty: int = 5) -> list:
    """
    Получаем список фото на загрузку из ВК
    """
    vk_client = VkApiClient(token=token, user_ids=user_id, api_version='5.131')
    try:
        vk_photos = vk_client.get_photos(album_id=album)['response']['items']
        photos_dict = {}
        return_list = []
        cnt = 0
        for photo in vk_photos:
            if cnt >= qty:
                break
            photo_name = str(photo['likes']['count'])
            if photo_name not in photos_dict.keys():
                photos_dict.setdefault(photo_name, get_biggest_photo(photo['sizes']))
            else:
                photo_name = f"{str(photo['likes']['count'])}_{str(photo['date'])}"
                photos_dict.setdefault(photo_name, get_biggest_photo(photo['sizes']))
            cnt += 1
        for file, details in photos_dict.items():
            return_list.append({'filename': f'{file}.jpg', 'size': details['size'], 'url': details['url']})
        return return_list
    except TypeError:
        print('Нет фотографий на загрузку')


with open('vktoken.txt', encoding='utf-8') as vk_file:
    # токен ВК из файла
    vk_token = vk_file.read()

with open('yatoken.txt', encoding='utf-8') as ya_file:
    # токен яндекс диска из файла
    ya_token = ya_file.read()

if __name__ == '__main__':
    user = input('Введите ID пользователя в ВК: ')
    quantity = int(input('Какое количество фотографий скачать? Введите цифру: '))
    albumid = input('С какого альбома берем фото? 1: фото со стены, 2: фото профиля, 3: сохраненные. Введите цифру: ' )
    albums = {'1': 'wall', '2': 'profile', '3': 'saved'}
    dir_name = 'VK_photos'
    res_list = get_vk_photos(user, vk_token, album=albums[albumid], qty=quantity)
    upload_photos_to_yad(res_list, ya_token, dir_name)

    # Сохраняем результат в файл
    with open('loaded_photos.json', 'w', encoding='utf-8') as file_obj:
        try:
            for d in res_list:
                d.pop('url', None)
            file_obj.write(json.dumps(res_list))
        except TypeError:
            print('Нет данных для сохранения')
