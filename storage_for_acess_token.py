access_token = input("Введите токен здесь или запишите токен в файле storage_for_acess_token: ")

#Единственный вариант решения, который нашел
import vk_api
import os
import json

def get_token():
    login = input('Введите логин: ')
    passw = input('Введите пароль: ')

    VK = vk_api.VkApi(login, passw)
    VK.auth()
    VK = VK.get_api()
    access_token = 0

    try:
        User = VK.users.get()
    except:
        print("Error")
    else:
        with open('vk_config.v2.json', 'r') as data_file:
            data = json.load(data_file)

        for xxx in data[login]['token'].keys():
            for yyy in data[login]['token'][xxx].keys():
                access_token = data[login]['token'][xxx][yyy]['access_token']
        os.remove('vk_config.v2.json')
    return access_token
