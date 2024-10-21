# redis.py
import redis

# Инициализация клиента
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

# Проверка подключения
try:
    redis_client.ping()
    print("Подключение к Redis успешно!")
except redis.ConnectionError as e:
    print(f"Ошибка подключения к Redis: {e}")

# Простой тест записи и чтения
test_key = "test_key"
redis_client.set(test_key, "Hello, Redis!")
value = redis_client.get(test_key)
# Получаем все ключи

# Получение всех ключей
keys = redis_client.keys('*')

# Вывод ключей и их значений (если требуется)
for key in keys:
    print(f"Key: {key.decode('utf-8')}, Value: {redis_client.get(key).decode('utf-8')}")

print(f"Значение по ключу '{test_key}': {value.decode('utf-8') if value else None}")