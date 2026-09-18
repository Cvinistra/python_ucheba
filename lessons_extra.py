# -*- coding: utf-8 -*-
"""
Дополнительные уроки Python.
Формат: "Тема": (эмодзи, объяснение, код_или_None, результат_или_None)
"""

LESSONS_EXTRA = {

# ---------- Раздел 1. Основы ----------
"Комментарии": ("💬", "Комментарии — это пояснения в коде, которые Python не выполняет. Однострочный комментарий начинается с #, а многострочный оформляется тройными кавычками.",
"""# Это однострочный комментарий
print("Привет")  # комментарий после кода

\"\"\"
Это
многострочный
комментарий
\"\"\"""", None),

"int / float": ("🔢", "int хранит целые числа, а float — дробные (с плавающей точкой). Python сам определяет тип по значению.",
"""age = 14          # int
price = 19.99     # float
print(type(age))
print(type(price))""",
"<class 'int'>\n<class 'float'>"),

"str / bool": ("🔤", "str — это строка (текст в кавычках), bool — логический тип, у которого только два значения: True и False.",
"""name = "Alex"        # str
is_online = True     # bool
print(type(name), type(is_online))""",
"<class 'str'> <class 'bool'>"),

"type()": ("🔍", "Функция type() показывает, к какому типу данных относится значение или переменная. Полезна для отладки.",
"""print(type(10))
print(type(10.5))
print(type("текст"))
print(type(True))""",
"<class 'int'>\n<class 'float'>\n<class 'str'>\n<class 'bool'>"),

# ---------- Раздел 2. Операторы ----------
"Арифметические": ("➕", "Арифметические операторы выполняют математические действия: сложение, вычитание, умножение, деление и другие.",
"""print(5 + 2)   # сложение → 7
print(5 - 2)   # вычитание → 3
print(5 * 2)   # умножение → 10
print(5 / 2)   # деление → 2.5
print(5 // 2)  # целочисленное деление → 2
print(5 % 2)   # остаток от деления → 1
print(5 ** 2)  # возведение в степень → 25"""),

"Сравнения": ("⚖️", "Операторы сравнения проверяют отношение между значениями и возвращают True или False.",
"""print(5 == 5)   # равно → True
print(5 != 3)   # не равно → True
print(5 > 3)    # больше → True
print(5 < 3)    # меньше → False
print(5 >= 5)   # больше или равно → True
print(5 <= 4)   # меньше или равно → False"""),

"Логические": ("🔗", "Логические операторы and, or и not объединяют или инвертируют условия.",
"""age = 20
print(age > 18 and age < 65)  # оба условия истинны → True
print(age < 10 or age > 18)   # хотя бы одно истинно → True
print(not age > 18)           # инверсия → False"""),

"Присваивания": ("✍️", "Операторы присваивания не только записывают значение в переменную, но и умеют сразу изменять его.",
"""x = 10
x += 5   # x = x + 5 → 15
x -= 3   # 12
x *= 2   # 24
x //= 5  # 4
print(x)"""),

"in / not in": ("🔎", "Операторы in и not in проверяют, содержится ли элемент в строке, списке или другой коллекции.",
"""fruits = ["яблоко", "банан"]
print("яблоко" in fruits)      # True
print("груша" not in fruits)   # True
print("а" in "банан")          # True"""),

"is / is not": ("🆔", "is и is not сравнивают, ссылаются ли переменные на один и тот же объект в памяти, а не равны ли их значения (для этого используют ==).",
"""a = None
print(a is None)      # True — правильная проверка на None
b = [1, 2]
c = [1, 2]
print(b == c)          # True — значения равны
print(b is c)          # False — это разные объекты"""),

"Приоритет операторов": ("📐", "У операторов есть приоритет выполнения: сначала скобки, затем степень, умножение и деление, потом сложение и вычитание, и только потом сравнения и логические операции.",
"""print(2 + 3 * 4)     # сначала умножение → 14
print((2 + 3) * 4)   # скобки меняют порядок → 20
print(2 + 3 > 4 and 1 < 2)  # сначала арифметика и сравнения, потом and"""),

# ---------- Раздел 3. Типы данных ----------
"list": ("📋", "list (список) — изменяемая упорядоченная коллекция элементов любого типа.",
"""fruits = ["яблоко", "банан", "вишня"]
fruits.append("апельсин")
print(fruits)""",
"['яблоко', 'банан', 'вишня', 'апельсин']"),

"tuple": ("📚", "tuple (кортеж) — упорядоченная коллекция, но неизменяемая: после создания элементы менять нельзя.",
"""point = (10, 20)
print(point[0])
# point[0] = 5  → вызовет ошибку TypeError"""),

"set": ("🔵", "set (множество) — неупорядоченная коллекция уникальных элементов, дубликаты автоматически удаляются.",
"""numbers = {1, 2, 2, 3, 3, 3}
print(numbers)""",
"{1, 2, 3}"),

"dict": ("📖", "dict (словарь) хранит данные парами «ключ — значение», доступ к значению идёт по ключу.",
"""user = {"name": "Alex", "age": 14}
print(user["name"])""",
"Alex"),

"None": ("⭕", "None — специальное значение, означающее «ничего» или «значение ещё не задано». Это не то же самое, что 0 или пустая строка.",
"""result = None
if result is None:
    print("Значения ещё нет")"""),

"bytes": ("🧬", "bytes — неизменяемая последовательность байтов. Используется для работы с бинарными данными и кодировками.",
"""data = "Привет".encode("utf-8")
print(data)
print(type(data))""",
"b'\\xd0\\x9f...' \n<class 'bytes'>"),

# ---------- Раздел 4. Строки ----------
"Создание строк": ("🔤", "Строки создаются в одинарных, двойных или тройных кавычках. Тройные кавычки позволяют писать текст в несколько строк.",
"""a = 'Привет'
b = "Привет"
c = \"\"\"Привет,
как дела?\"\"\""""),

"Индексы": ("📍", "У строк и списков есть индексы — номера позиций элементов, начиная с 0. Отрицательные индексы отсчитывают с конца.",
"""word = "Python"
print(word[0])    # 'P' — первый символ
print(word[-1])   # 'n' — последний символ"""),

"Срезы": ("✂️", "Срез (slice) позволяет получить часть строки или списка по шаблону [начало:конец:шаг].",
"""word = "Python"
print(word[0:3])   # 'Pyt'
print(word[:2])    # 'Py'
print(word[::-1])  # 'nohtyP' — разворот строки"""),

"len()": ("📏", "Функция len() возвращает длину строки, списка, кортежа, словаря или другой коллекции.",
"""print(len("Python"))       # 6
print(len([1, 2, 3, 4]))   # 4"""),

"upper()": ("🔠", "Метод upper() переводит все буквы строки в верхний регистр.",
"""text = "python"
print(text.upper())""",
"PYTHON"),

"lower()": ("🔡", "Метод lower() переводит все буквы строки в нижний регистр.",
"""text = "PYTHON"
print(text.lower())""",
"python"),

"strip()": ("🧹", "Метод strip() убирает пробелы (и другие указанные символы) в начале и конце строки.",
"""text = "   Привет   "
print(text.strip())""",
"'Привет'"),

"replace()": ("🔁", "Метод replace() заменяет все вхождения одной подстроки на другую.",
"""text = "Я люблю Java"
print(text.replace("Java", "Python"))""",
"Я люблю Python"),

"split()": ("✂️", "Метод split() разбивает строку на список подстрок по разделителю (по умолчанию — по пробелу).",
"""text = "яблоко,банан,вишня"
print(text.split(","))""",
"['яблоко', 'банан', 'вишня']"),

"join()": ("🧵", "Метод join() собирает список строк в одну строку через указанный разделитель — обратная операция к split().",
"""fruits = ["яблоко", "банан", "вишня"]
print(", ".join(fruits))""",
"яблоко, банан, вишня"),

"find()": ("🔎", "Метод find() ищет подстроку и возвращает индекс первого вхождения, либо -1, если ничего не найдено.",
"""text = "Привет, Python!"
print(text.find("Python"))   # 8
print(text.find("Java"))     # -1"""),

"count()": ("🔢", "Метод count() считает, сколько раз элемент или подстрока встречается в строке, списке или кортеже.",
"""text = "банан"
print(text.count("а"))    # 2
print([1, 2, 2, 3].count(2))  # 2"""),

"startswith()": ("🏁", "Метод startswith() проверяет, начинается ли строка с указанной подстроки.",
"""text = "Python — это круто"
print(text.startswith("Python"))   # True"""),

"endswith()": ("🏆", "Метод endswith() проверяет, заканчивается ли строка указанной подстрокой.",
"""filename = "photo.png"
print(filename.endswith(".png"))   # True"""),

"f-строки": ("🧩", "f-строки (f-strings) позволяют подставлять значения переменных прямо внутрь строки через фигурные скобки.",
"""name = "Alex"
age = 14
print(f"Меня зовут {name}, мне {age} лет")
print(f"Через год будет {age + 1}")""",
"Меня зовут Alex, мне 14 лет\nЧерез год будет 15"),

# ---------- Раздел 5. Списки ----------
"Создание": ("📋", "Список создаётся квадратными скобками, элементы через запятую. Список может хранить значения разных типов.",
"""numbers = [1, 2, 3]
mixed = ["текст", 10, True]
empty = []"""),

"append()": ("➕", "Метод append() добавляет один элемент в конец списка.",
"""fruits = ["яблоко"]
fruits.append("банан")
print(fruits)""",
"['яблоко', 'банан']"),

"extend()": ("➕", "Метод extend() добавляет в список сразу несколько элементов из другого списка.",
"""a = [1, 2]
a.extend([3, 4])
print(a)""",
"[1, 2, 3, 4]"),

"insert()": ("📥", "Метод insert(индекс, значение) вставляет элемент на конкретную позицию в списке.",
"""fruits = ["яблоко", "вишня"]
fruits.insert(1, "банан")
print(fruits)""",
"['яблоко', 'банан', 'вишня']"),

"remove()": ("🗑", "Метод remove() удаляет из списка первое найденное совпадение с указанным значением.",
"""fruits = ["яблоко", "банан", "яблоко"]
fruits.remove("яблоко")
print(fruits)""",
"['банан', 'яблоко']"),

"pop()": ("📤", "Метод pop() удаляет элемент по индексу (по умолчанию — последний) и возвращает его значение.",
"""fruits = ["яблоко", "банан"]
last = fruits.pop()
print(last, fruits)""",
"банан ['яблоко']"),

"clear()": ("🧼", "Метод clear() удаляет все элементы из списка или словаря, оставляя его пустым.",
"""fruits = ["яблоко", "банан"]
fruits.clear()
print(fruits)""",
"[]"),

"index()": ("📍", "Метод index() возвращает индекс первого вхождения элемента в списке.",
"""fruits = ["яблоко", "банан", "вишня"]
print(fruits.index("вишня"))""",
"2"),

"sort()": ("🔃", "Метод sort() сортирует список по возрастанию на месте. Для убывания используют sort(reverse=True).",
"""numbers = [3, 1, 2]
numbers.sort()
print(numbers)
numbers.sort(reverse=True)
print(numbers)""",
"[1, 2, 3]\n[3, 2, 1]"),

"reverse()": ("🔄", "Метод reverse() разворачивает порядок элементов списка на обратный.",
"""numbers = [1, 2, 3]
numbers.reverse()
print(numbers)""",
"[3, 2, 1]"),

"copy()": ("📄", "Метод copy() создаёт независимую копию списка или словаря, чтобы изменения одного не влияли на другой.",
"""a = [1, 2, 3]
b = a.copy()
b.append(4)
print(a, b)""",
"[1, 2, 3] [1, 2, 3, 4]"),

"list comprehension": ("🧠", "List comprehension — компактный способ создать список на основе цикла и условия в одной строке.",
"""squares = [x ** 2 for x in range(5)]
print(squares)
even = [x for x in range(10) if x % 2 == 0]
print(even)""",
"[0, 1, 4, 9, 16]\n[0, 2, 4, 6, 8]"),

# ---------- Раздел 6. Кортежи ----------
"Распаковка": ("📦", "Распаковка позволяет за один раз присвоить элементы кортежа или списка нескольким переменным.",
"""point = (10, 20)
x, y = point
print(x, y)

a, b, c = [1, 2, 3]
print(a, b, c)""",
"10 20\n1 2 3"),

# ---------- Раздел 7. Множества ----------
"add()": ("➕", "Метод add() добавляет один элемент в множество (set). Если такой элемент уже есть, ничего не изменится.",
"""nums = {1, 2, 3}
nums.add(4)
nums.add(2)
print(nums)""",
"{1, 2, 3, 4}"),

"discard()": ("🗑", "Метод discard() удаляет элемент из множества, но, в отличие от remove(), не вызывает ошибку, если элемента нет.",
"""nums = {1, 2, 3}
nums.discard(5)   # не вызовет ошибку
nums.discard(2)
print(nums)""",
"{1, 3}"),

"union()": ("🔗", "Метод union() (или оператор |) объединяет два множества, возвращая все уникальные элементы из обоих.",
"""a = {1, 2, 3}
b = {3, 4, 5}
print(a.union(b))""",
"{1, 2, 3, 4, 5}"),

"intersection()": ("🔗", "Метод intersection() (или оператор &) возвращает элементы, которые есть в обоих множествах одновременно.",
"""a = {1, 2, 3}
b = {2, 3, 4}
print(a.intersection(b))""",
"{2, 3}"),

"difference()": ("➖", "Метод difference() (или оператор -) возвращает элементы, которые есть в первом множестве, но отсутствуют во втором.",
"""a = {1, 2, 3}
b = {2, 3, 4}
print(a.difference(b))""",
"{1}"),

"frozenset": ("🧊", "frozenset — неизменяемая версия множества. После создания элементы добавить или удалить нельзя.",
"""fs = frozenset([1, 2, 3])
print(fs)
# fs.add(4) → вызовет ошибку AttributeError"""),

# ---------- Раздел 8. Словари ----------
"Ключи": ("🔑", "Ключи словаря — уникальные идентификаторы значений. Ключом может быть строка, число или другой неизменяемый тип.",
"""user = {"name": "Alex", "age": 14}
print(list(user.keys()))""",
"['name', 'age']"),

"Значения": ("🎯", "Значения словаря — данные, к которым можно обратиться по ключу. Значением может быть что угодно, включая список или другой словарь.",
"""user = {"name": "Alex", "age": 14}
print(list(user.values()))""",
"['Alex', 14]"),

"items()": ("🧾", "Метод items() возвращает пары (ключ, значение) — удобно для перебора словаря в цикле.",
"""user = {"name": "Alex", "age": 14}
for key, value in user.items():
    print(key, "→", value)""",
"name → Alex\nage → 14"),

"keys()": ("🔑", "Метод keys() возвращает все ключи словаря в виде специального объекта, который можно перебрать в цикле.",
"""user = {"name": "Alex", "age": 14}
for key in user.keys():
    print(key)"""),

"values()": ("🎯", "Метод values() возвращает все значения словаря.",
"""user = {"name": "Alex", "age": 14}
for value in user.values():
    print(value)"""),

"get()": ("🔍", "Метод get() безопасно достаёт значение по ключу и не вызывает ошибку, если ключа нет — вместо этого можно указать значение по умолчанию.",
"""user = {"name": "Alex"}
print(user.get("age"))         # None, ошибки нет
print(user.get("age", 18))     # 18 — значение по умолчанию"""),

"update()": ("🔄", "Метод update() добавляет новые пары ключ-значение в словарь или обновляет существующие.",
"""user = {"name": "Alex"}
user.update({"age": 14, "name": "Alexey"})
print(user)""",
"{'name': 'Alexey', 'age': 14}"),

"dictionary comprehension": ("🧠", "Dictionary comprehension позволяет создать словарь в одну строку на основе цикла.",
"""squares = {x: x ** 2 for x in range(5)}
print(squares)""",
"{0: 0, 1: 1, 2: 4, 3: 9, 4: 16}"),

# ---------- Раздел 9. Циклы ----------
"range()": ("🔢", "range() создаёт последовательность чисел — обычно используется вместе с циклом for.",
"""for i in range(3):
    print(i)
for i in range(2, 10, 2):
    print(i)""",
"0\n1\n2\n2\n4\n6\n8"),

"for по списку": ("📋", "Цикл for может перебирать элементы списка по одному, без использования индексов.",
"""fruits = ["яблоко", "банан", "вишня"]
for fruit in fruits:
    print(fruit)"""),

"for по строке": ("🔤", "Цикл for может перебирать строку посимвольно.",
"""for letter in "Python":
    print(letter)"""),

"for по словарю": ("📖", "При переборе словаря циклом for по умолчанию идут ключи; чтобы получить и значения, используют items().",
"""user = {"name": "Alex", "age": 14}
for key in user:
    print(key, user[key])"""),

"while True": ("🔁", "while True создаёт бесконечный цикл — его нужно останавливать вручную через break по условию.",
"""while True:
    answer = input("Введи 'стоп' для выхода: ")
    if answer == "стоп":
        break
    print("Ты ввёл:", answer)"""),

"break": ("🛑", "Оператор break немедленно прерывает выполнение цикла, даже если условие цикла ещё истинно.",
"""for i in range(10):
    if i == 3:
        break
    print(i)""",
"0\n1\n2"),

"continue": ("⏭", "Оператор continue пропускает оставшуюся часть текущей итерации и переходит к следующей.",
"""for i in range(5):
    if i == 2:
        continue
    print(i)""",
"0\n1\n3\n4"),

"else у цикла": ("🔚", "Блок else у цикла for/while выполняется, если цикл завершился без break.",
"""for i in range(3):
    print(i)
else:
    print("Цикл завершён без break")"""),

"вложенные циклы": ("🪆", "Один цикл можно поместить внутрь другого — например, для перебора строк и столбцов таблицы.",
"""for i in range(3):
    for j in range(2):
        print(i, j)"""),

# ---------- Раздел 10. Условия ----------
"elif": ("🔀", "elif (сокращение от else if) позволяет проверить дополнительное условие, если предыдущее было ложным.",
"""age = 16
if age < 12:
    print("Ребёнок")
elif age < 18:
    print("Подросток")
else:
    print("Взрослый")""",
"Подросток"),

"else": ("🔚", "Блок else выполняется, если ни одно из предыдущих условий if/elif не оказалось истинным.",
"""age = 20
if age < 18:
    print("Нельзя")
else:
    print("Можно")""",
"Можно"),

"вложенные условия": ("🪆", "Одно условие if можно разместить внутри другого, чтобы проверять более сложные комбинации.",
"""age = 20
has_id = True
if age >= 18:
    if has_id:
        print("Доступ разрешён")
    else:
        print("Нужен документ")"""),

"тернарный оператор": ("⚡", "Тернарный оператор позволяет записать простое if/else в одну строку.",
"""age = 20
status = "взрослый" if age >= 18 else "ребёнок"
print(status)""",
"взрослый"),

"match / case": ("🎛", "match/case (появился в Python 3.10) — аналог switch из других языков, удобен для сравнения значения с несколькими вариантами.",
"""command = "start"

match command:
    case "start":
        print("Запуск")
    case "stop":
        print("Остановка")
    case _:
        print("Неизвестная команда")""",
"Запуск"),

# ---------- Раздел 11. Функции ----------
"параметры": ("📥", "Параметры — это переменные, объявленные в скобках функции, через которые внутрь передаются данные.",
"""def greet(name):   # name — параметр
    print(f"Привет, {name}!")

greet("Alex")   # "Alex" — аргумент"""),

"аргументы": ("📤", "Аргументы — конкретные значения, которые передаются в функцию при её вызове.",
"""def add(a, b):
    return a + b

print(add(2, 3))   # 2 и 3 — аргументы""",
"5"),

"*args": ("📦", "*args позволяет функции принимать любое количество позиционных аргументов, которые попадут в кортеж.",
"""def total(*args):
    return sum(args)

print(total(1, 2, 3, 4))""",
"10"),

"**kwargs": ("📦", "**kwargs позволяет функции принимать любое количество именованных аргументов в виде словаря.",
"""def profile(**kwargs):
    for key, value in kwargs.items():
        print(key, "=", value)

profile(name="Alex", age=14)"""),

"значения по умолчанию": ("⚙️", "Параметру можно задать значение по умолчанию — тогда его можно не указывать при вызове функции.",
"""def greet(name, greeting="Привет"):
    print(f"{greeting}, {name}!")

greet("Alex")
greet("Alex", "Хай")""",
"Привет, Alex!\nХай, Alex!"),

"keyword arguments": ("🏷", "Именованные аргументы передаются в формате имя=значение, что делает вызов функции понятнее и позволяет менять их порядок.",
"""def describe(name, age):
    print(f"{name}, {age} лет")

describe(age=14, name="Alex")""",
"Alex, 14 лет"),

"lambda": ("λ", "lambda создаёт маленькую анонимную функцию в одну строку — удобно для коротких операций внутри других функций.",
"""square = lambda x: x ** 2
print(square(5))

numbers = [1, 2, 3]
doubled = list(map(lambda x: x * 2, numbers))
print(doubled)""",
"25\n[2, 4, 6]"),

"область видимости": ("🌐", "Область видимости определяет, где переменная доступна. Переменные внутри функции — локальные, снаружи — глобальные.",
"""x = 10   # глобальная

def show():
    x = 5   # локальная, не влияет на глобальную
    print(x)

show()
print(x)""",
"5\n10"),

"global": ("🌍", "Ключевое слово global позволяет изменить глобальную переменную прямо внутри функции.",
"""counter = 0

def increment():
    global counter
    counter += 1

increment()
print(counter)""",
"1"),

"nonlocal": ("🔗", "nonlocal позволяет функции изменить переменную из внешней (объемлющей) функции, а не глобальную.",
"""def outer():
    count = 0
    def inner():
        nonlocal count
        count += 1
    inner()
    print(count)

outer()""",
"1"),

"рекурсия": ("🌀", "Рекурсия — когда функция вызывает саму себя. Обязательно нужно базовое условие, иначе получится бесконечный вызов.",
"""def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

print(factorial(5))""",
"120"),

# ---------- Раздел 12. Comprehension ----------
"dict comprehension": ("🧠", "Словарь можно создать в одну строку тем же способом, что и список — через comprehension.",
"""squares = {x: x ** 2 for x in range(5)}
print(squares)""",
"{0: 0, 1: 1, 2: 4, 3: 9, 4: 16}"),

"set comprehension": ("🧠", "Множество тоже можно создать через comprehension — синтаксис похож на список, но в фигурных скобках.",
"""unique_lengths = {len(word) for word in ["кот", "пёс", "слон"]}
print(unique_lengths)""",
"{3, 4}"),

"условия": ("❓", "Внутри comprehension можно добавить условие if, чтобы фильтровать элементы, попадающие в результат.",
"""even = [x for x in range(10) if x % 2 == 0]
print(even)""",
"[0, 2, 4, 6, 8]"),

"вложенные comprehension": ("🪆", "Comprehension можно вкладывать друг в друга — например, чтобы «развернуть» список списков в один плоский список.",
"""matrix = [[1, 2], [3, 4]]
flat = [num for row in matrix for num in row]
print(flat)""",
"[1, 2, 3, 4]"),

# ---------- Раздел 13. Ошибки и исключения ----------
"SyntaxError": ("⚠️", "SyntaxError возникает, когда код написан с нарушением синтаксиса Python — например, забыли двоеточие или скобку.",
"""# if True
#     print("ошибка") — нет двоеточия после True → SyntaxError"""),

"TypeError": ("⚠️", "TypeError возникает при попытке выполнить операцию над несовместимыми типами данных.",
"""# print("2" + 2) → TypeError: нельзя сложить str и int
print(str(2) + "2")  # правильно: сначала привести к одному типу"""),

"ValueError": ("⚠️", "ValueError возникает, когда функция получает значение правильного типа, но некорректное по содержанию.",
"""# int("текст") → ValueError: невозможно превратить строку в число
print(int("123"))  # а так — сработает"""),

"IndexError": ("⚠️", "IndexError возникает при обращении к индексу списка или строки, которого не существует.",
"""fruits = ["яблоко", "банан"]
# print(fruits[5]) → IndexError
print(fruits[1])   # правильный индекс"""),

"KeyError": ("⚠️", "KeyError возникает при обращении к несуществующему ключу словаря.",
"""user = {"name": "Alex"}
# print(user["age"]) → KeyError
print(user.get("age"))   # безопасный способ"""),

"NameError": ("⚠️", "NameError возникает при обращении к переменной, которая ещё не была создана.",
"""# print(unknown_variable) → NameError
x = 10
print(x)   # так корректно"""),

"try": ("🛡", "Блок try содержит код, который может вызвать ошибку. Python попробует его выполнить и не остановит программу при сбое.",
"""try:
    result = 10 / 0
except ZeroDivisionError:
    print("Деление на ноль недопустимо")"""),

"except": ("🧯", "Блок except перехватывает ошибку, возникшую в try, и позволяет обработать её вместо аварийной остановки программы.",
"""try:
    number = int(input("Введи число: "))
except ValueError:
    print("Это не число!")"""),

"finally": ("🏁", "Блок finally выполняется всегда — независимо от того, была ошибка или нет. Часто используется для очистки ресурсов.",
"""try:
    file = open("data.txt")
except FileNotFoundError:
    print("Файл не найден")
finally:
    print("Попытка завершена")"""),

"raise": ("🚨", "Оператор raise позволяет самостоятельно вызвать исключение, когда в коде обнаружена недопустимая ситуация.",
"""age = -5
if age < 0:
    raise ValueError("Возраст не может быть отрицательным")"""),

"создание своих исключений": ("🏗", "Свои классы исключений создаются наследованием от Exception — это делает ошибки в проекте более понятными.",
"""class NotEnoughMoneyError(Exception):
    pass

def buy(price, balance):
    if price > balance:
        raise NotEnoughMoneyError("Недостаточно средств")"""),

# ---------- Раздел 14. Файлы ----------
"open()": ("📂", "Функция open() открывает файл для чтения, записи или дополнения. Режим указывается вторым аргументом: 'r', 'w', 'a'.",
"""file = open("data.txt", "r", encoding="utf-8")
content = file.read()
file.close()"""),

"read()": ("📖", "Метод read() читает весь файл целиком и возвращает его содержимое строкой.",
"""with open("data.txt", "r", encoding="utf-8") as f:
    content = f.read()
    print(content)"""),

"readline()": ("📄", "Метод readline() читает из файла только одну строку за раз.",
"""with open("data.txt", "r", encoding="utf-8") as f:
    first_line = f.readline()
    print(first_line)"""),

"readlines()": ("📑", "Метод readlines() читает весь файл и возвращает список строк.",
"""with open("data.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()
    print(lines)"""),

"write()": ("✍️", "Метод write() записывает строку в файл, открытый в режиме записи ('w') или дополнения ('a').",
"""with open("data.txt", "w", encoding="utf-8") as f:
    f.write("Привет, файл!")"""),

"writelines()": ("📝", "Метод writelines() записывает в файл сразу список строк.",
"""lines = ["Строка 1\\n", "Строка 2\\n"]
with open("data.txt", "w", encoding="utf-8") as f:
    f.writelines(lines)"""),

"with": ("🔒", "Конструкция with автоматически закрывает файл (или другой ресурс) после завершения блока, даже если возникнет ошибка.",
"""with open("data.txt", "r", encoding="utf-8") as f:
    content = f.read()
# файл уже закрыт автоматически"""),

"txt": ("📃", "Обычные текстовые файлы .txt хранят простой текст без форматирования — самый простой формат для чтения и записи.",
"""with open("notes.txt", "a", encoding="utf-8") as f:
    f.write("Новая заметка\\n")"""),

"JSON": ("🧾", "JSON — формат для хранения структурированных данных (похож на словари Python). Модуль json умеет читать и сохранять такие файлы.",
"""import json

data = {"name": "Alex", "age": 14}
with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False)

with open("data.json", "r", encoding="utf-8") as f:
    loaded = json.load(f)
print(loaded)"""),

"CSV": ("📊", "CSV — табличный текстовый формат, где значения разделены запятыми. Модуль csv упрощает чтение и запись таких файлов.",
"""import csv

with open("users.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["name", "age"])
    writer.writerow(["Alex", 14])"""),

# ---------- Раздел 15. Модули ----------
"import": ("📦", "import подключает к программе модуль — файл с уже готовым кодом (функциями, классами), который можно переиспользовать.",
"""import math
print(math.sqrt(16))""",
"4.0"),

"from ... import": ("📦", "from модуль import имя позволяет импортировать конкретную функцию или класс, чтобы обращаться к ней напрямую, без имени модуля.",
"""from math import sqrt
print(sqrt(25))""",
"5.0"),

"as": ("🏷", "Ключевое слово as задаёт удобный псевдоним модулю или объекту при импорте.",
"""import numpy as np
import pandas as pd"""),

"math": ("➗", "Модуль math предоставляет математические функции: корень, округление, тригонометрию, число π и другие.",
"""import math
print(math.sqrt(9))
print(math.pi)
print(math.ceil(4.2))
print(math.floor(4.8))""",
"3.0\n3.141592653589793\n5\n4"),

"random": ("🎲", "Модуль random позволяет генерировать случайные числа и выбирать случайные элементы из последовательностей.",
"""import random
print(random.randint(1, 6))     # случайное число от 1 до 6
print(random.choice(["орёл", "решка"]))
fruits = ["яблоко", "банан", "вишня"]
random.shuffle(fruits)
print(fruits)"""),

"datetime": ("📅", "Модуль datetime позволяет работать с датами и временем — получать текущую дату, форматировать её, вычислять разницу.",
"""from datetime import datetime

now = datetime.now()
print(now)
print(now.strftime("%d.%m.%Y %H:%M"))"""),

"os": ("🗂", "Модуль os даёт доступ к операционной системе: работа с путями, файлами, переменными окружения.",
"""import os
print(os.getcwd())              # текущая папка
print(os.listdir("."))          # список файлов в папке
token = os.getenv("BOT_TOKEN")  # переменная окружения"""),

"sys": ("⚙️", "Модуль sys даёт доступ к параметрам интерпретатора Python: аргументам командной строки, выходу из программы и др.",
"""import sys
print(sys.version)      # версия Python
# sys.exit()             # завершить программу"""),

"pathlib": ("📁", "pathlib — современный способ работы с путями к файлам через объекты Path вместо строк.",
"""from pathlib import Path

path = Path("data") / "file.txt"
print(path)
print(path.exists())"""),

"создание своих модулей": ("🏗", "Любой файл .py можно импортировать в другой файл как модуль — так код удобно разбивать на части.",
"""# файл helpers.py
def greet(name):
    return f"Привет, {name}!"

# файл main.py
from helpers import greet
print(greet("Alex"))"""),

# ---------- Раздел 16. ООП ----------
"Что такое класс": ("🏗", "Класс — это шаблон (чертёж) для создания объектов, который описывает их данные (атрибуты) и поведение (методы).",
"""class Dog:
    def bark(self):
        print("Гав!")

rex = Dog()
rex.bark()"""),

"object": ("🧱", "object — базовый класс, от которого неявно наследуются все классы в Python.",
"""class Dog:
    pass

print(isinstance(Dog(), object))""",
"True"),

"__init__": ("🏗", "__init__ — специальный метод-конструктор, который автоматически вызывается при создании объекта и задаёт его начальные атрибуты.",
"""class Player:
    def __init__(self, name):
        self.name = name

player = Player("Alex")
print(player.name)""",
"Alex"),

"self": ("👤", "self — это ссылка на текущий объект внутри методов класса. Через него методы получают доступ к атрибутам объекта.",
"""class Player:
    def __init__(self, name):
        self.name = name

    def greet(self):
        print(f"Привет, я {self.name}")

Player("Alex").greet()""",
"Привет, я Alex"),

"атрибуты": ("🏷", "Атрибуты — это переменные, которые хранят данные, принадлежащие объекту.",
"""class Player:
    def __init__(self, name, health):
        self.name = name
        self.health = health

p = Player("Alex", 100)
print(p.health)""",
"100"),

"методы": ("🧩", "Методы — это функции, определённые внутри класса, которые описывают поведение объектов этого класса.",
"""class Player:
    def __init__(self, health):
        self.health = health

    def take_damage(self, amount):
        self.health -= amount

p = Player(100)
p.take_damage(30)
print(p.health)""",
"70"),

"наследование": ("🌳", "Наследование позволяет создать новый класс на основе существующего, переиспользуя и расширяя его функциональность.",
"""class Animal:
    def speak(self):
        print("Издаю звук")

class Dog(Animal):
    def speak(self):
        print("Гав!")

Dog().speak()""",
"Гав!"),

"super()": ("⬆️", "super() позволяет вызвать метод родительского класса из дочернего — часто используется в __init__.",
"""class Animal:
    def __init__(self, name):
        self.name = name

class Dog(Animal):
    def __init__(self, name, breed):
        super().__init__(name)
        self.breed = breed

d = Dog("Рекс", "овчарка")
print(d.name, d.breed)""",
"Рекс овчарка"),

"полиморфизм": ("🎭", "Полиморфизм — возможность объектов разных классов одинаково реагировать на один и тот же вызов метода, но по-своему.",
"""class Cat:
    def speak(self):
        print("Мяу")

class Dog:
    def speak(self):
        print("Гав")

for animal in [Cat(), Dog()]:
    animal.speak()"""),

"инкапсуляция": ("🔒", "Инкапсуляция — сокрытие внутренних деталей объекта. В Python приватность обозначается соглашением: имя атрибута с подчёркиванием _ или __.",
"""class Account:
    def __init__(self, balance):
        self.__balance = balance   # приватный атрибут

    def get_balance(self):
        return self.__balance"""),

"@property": ("🏷", "Декоратор @property позволяет обращаться к методу как к обычному атрибуту, без круглых скобок — удобно для вычисляемых значений.",
"""class Circle:
    def __init__(self, radius):
        self.radius = radius

    @property
    def area(self):
        return 3.14 * self.radius ** 2

c = Circle(5)
print(c.area)   # без скобок!""",
"78.5"),

"classmethod": ("🏫", "@classmethod создаёт метод, который получает не объект (self), а сам класс (cls) — часто используется для альтернативных конструкторов.",
"""class Player:
    count = 0

    def __init__(self):
        Player.count += 1

    @classmethod
    def total_players(cls):
        return cls.count"""),

"staticmethod": ("🧰", "@staticmethod создаёт метод, который не зависит ни от объекта, ни от класса — по сути обычная функция, логически связанная с классом.",
"""class MathHelper:
    @staticmethod
    def add(a, b):
        return a + b

print(MathHelper.add(2, 3))""",
"5"),

"dataclass": ("🗃", "Декоратор @dataclass автоматически создаёт __init__ и другие методы для классов, которые в основном просто хранят данные.",
"""from dataclasses import dataclass

@dataclass
class Point:
    x: int
    y: int

p = Point(1, 2)
print(p)""",
"Point(x=1, y=2)"),

"магические методы": ("✨", "Магические методы (с двойным подчёркиванием, например __str__, __len__, __add__) позволяют управлять поведением встроенных операций для своих классов.",
"""class Point:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y)

    def __str__(self):
        return f"({self.x}, {self.y})"

print(Point(1, 2) + Point(3, 4))""",
"(4, 6)"),

# ---------- Раздел 17. Продвинутый Python ----------
"итераторы": ("🔁", "Итератор — объект, который умеет по очереди отдавать элементы через метод __next__(), пока они не закончатся.",
"""numbers = [1, 2, 3]
it = iter(numbers)
print(next(it))
print(next(it))"""),

"iter()": ("🔁", "Функция iter() превращает коллекцию (список, кортеж) в объект-итератор.",
"""nums = iter([10, 20, 30])
print(next(nums))""",
"10"),

"next()": ("⏭", "Функция next() возвращает следующий элемент итератора. Когда элементы заканчиваются, возникает StopIteration.",
"""it = iter([1, 2])
print(next(it))
print(next(it))
# print(next(it)) → StopIteration"""),

"генераторы": ("⚡", "Генератор — функция с yield, которая возвращает значения по одному, не создавая сразу весь список в памяти.",
"""def count_up_to(n):
    i = 1
    while i <= n:
        yield i
        i += 1

for number in count_up_to(3):
    print(number)"""),

"yield": ("⚡", "yield превращает обычную функцию в генератор: вместо return значение отдаётся, а выполнение функции приостанавливается до следующего вызова.",
"""def numbers():
    yield 1
    yield 2
    yield 3

for n in numbers():
    print(n)"""),

"декораторы": ("🎀", "Декоратор — функция, которая «оборачивает» другую функцию, добавляя ей новое поведение без изменения исходного кода.",
"""def logger(func):
    def wrapper(*args, **kwargs):
        print(f"Вызов функции {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

@logger
def greet():
    print("Привет!")

greet()"""),

"замыкания": ("🔐", "Замыкание — внутренняя функция, которая «запоминает» переменные из внешней функции даже после её завершения.",
"""def make_counter():
    count = 0
    def counter():
        nonlocal count
        count += 1
        return count
    return counter

my_counter = make_counter()
print(my_counter())
print(my_counter())""",
"1\n2"),

"map()": ("🗺", "Функция map() применяет заданную функцию к каждому элементу коллекции и возвращает новый набор результатов.",
"""numbers = [1, 2, 3]
doubled = list(map(lambda x: x * 2, numbers))
print(doubled)""",
"[2, 4, 6]"),

"filter()": ("🚰", "Функция filter() отбирает из коллекции только те элементы, для которых функция-условие вернула True.",
"""numbers = [1, 2, 3, 4, 5]
even = list(filter(lambda x: x % 2 == 0, numbers))
print(even)""",
"[2, 4]"),

"zip()": ("🤐", "Функция zip() объединяет несколько коллекций поэлементно в пары (или кортежи).",
"""names = ["Alex", "Anna"]
ages = [14, 15]
for name, age in zip(names, ages):
    print(name, age)""",
"Alex 14\nAnna 15"),

"enumerate()": ("🔢", "Функция enumerate() добавляет к элементам коллекции их индекс — удобно при переборе цикла for.",
"""fruits = ["яблоко", "банан"]
for index, fruit in enumerate(fruits):
    print(index, fruit)""",
"0 яблоко\n1 банан"),

"any()": ("✅", "Функция any() возвращает True, если хотя бы один элемент коллекции истинный.",
"""numbers = [0, 0, 3]
print(any(numbers))""",
"True"),

"all()": ("✅", "Функция all() возвращает True, только если все элементы коллекции истинные.",
"""numbers = [1, 2, 3]
print(all(numbers))
print(all([1, 0, 3]))""",
"True\nFalse"),

"functools": ("🧰", "Модуль functools содержит полезные инструменты для функций: кэширование результатов, частичное применение аргументов и другое.",
"""from functools import lru_cache

@lru_cache
def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)

print(fib(30))"""),

# ---------- Раздел 18. Асинхронность ----------
"await": ("⏳", "await используется внутри async-функции, чтобы дождаться завершения другой асинхронной операции, не блокируя всю программу.",
"""import asyncio

async def main():
    print("Начало")
    await asyncio.sleep(1)
    print("Через секунду")

asyncio.run(main())"""),

"asyncio": ("🧵", "asyncio — стандартная библиотека Python для написания асинхронного кода на основе event loop (событийного цикла).",
"""import asyncio

async def hello():
    print("Привет из asyncio!")

asyncio.run(hello())"""),

"coroutine": ("🌀", "Корутина — результат вызова async-функции. Сама по себе она не выполняется, пока её не запустят через await или asyncio.run().",
"""async def say_hi():
    print("Привет!")

coro = say_hi()   # это ещё не выполнение, а объект-корутина
# await coro       — а вот так она выполнится"""),

"Task": ("📋", "asyncio.create_task() запускает корутину «в фоне», позволяя выполнять несколько асинхронных операций параллельно.",
"""import asyncio

async def worker(name):
    await asyncio.sleep(1)
    print(f"{name} готов")

async def main():
    task1 = asyncio.create_task(worker("A"))
    task2 = asyncio.create_task(worker("B"))
    await task1
    await task2

asyncio.run(main())"""),

"gather()": ("🤝", "asyncio.gather() запускает сразу несколько корутин и ждёт завершения всех из них.",
"""import asyncio

async def task(n):
    await asyncio.sleep(1)
    return n * 2

async def main():
    results = await asyncio.gather(task(1), task(2), task(3))
    print(results)

asyncio.run(main())""",
"[2, 4, 6]"),

"sleep()": ("😴", "asyncio.sleep() — асинхронная пауза: не блокирует программу, позволяя выполняться другим задачам в это время.",
"""import asyncio

async def main():
    print("Ждём...")
    await asyncio.sleep(2)
    print("Готово!")

asyncio.run(main())"""),

"Queue": ("📬", "asyncio.Queue — асинхронная очередь для передачи данных между корутинами, например между «производителем» и «потребителем» задач.",
"""import asyncio

async def main():
    queue = asyncio.Queue()
    await queue.put("задача")
    item = await queue.get()
    print(item)

asyncio.run(main())"""),

"async context manager": ("🔒", "Асинхронный контекстный менеджер (async with) используется для ресурсов, открытие и закрытие которых требует await — например, сетевых соединений.",
"""import aiohttp

async def fetch(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()"""),

# ---------- Раздел 19. Базы данных ----------
"SQL": ("🗄", "SQL (Structured Query Language) — язык запросов для работы с реляционными базами данных: получение, добавление, изменение и удаление данных.",
"""SELECT * FROM users WHERE age > 18;"""),

"sqlite3": ("💾", "sqlite3 — встроенный модуль Python для работы с SQLite базами данных без установки дополнительных программ.",
"""import sqlite3

conn = sqlite3.connect("app.db")
cursor = conn.cursor()
cursor.execute("SELECT * FROM users")
print(cursor.fetchall())
conn.close()"""),

"CREATE": ("🏗", "SQL-команда CREATE TABLE создаёт новую таблицу с заданными столбцами и их типами.",
"""CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name TEXT,
    age INTEGER
);"""),

"SELECT": ("🔎", "SQL-команда SELECT извлекает данные из таблицы, можно указывать конкретные столбцы и условия отбора.",
"""SELECT name, age FROM users WHERE age >= 18;"""),

"INSERT": ("➕", "SQL-команда INSERT INTO добавляет новую запись (строку) в таблицу.",
"""INSERT INTO users (name, age) VALUES ('Alex', 14);"""),

"UPDATE": ("✏️", "SQL-команда UPDATE изменяет значения в существующих записях таблицы по заданному условию.",
"""UPDATE users SET age = 15 WHERE name = 'Alex';"""),

"DELETE": ("🗑", "SQL-команда DELETE удаляет записи из таблицы, подходящие под условие WHERE.",
"""DELETE FROM users WHERE age < 0;"""),

"WHERE": ("🔍", "WHERE задаёт условие отбора строк для SELECT, UPDATE и DELETE — без него операция затронет все строки таблицы.",
"""SELECT * FROM users WHERE age > 18 AND name LIKE 'A%';"""),

"JOIN": ("🔗", "JOIN объединяет данные из двух таблиц по связующему полю, например user_id.",
"""SELECT users.name, orders.total
FROM users
JOIN orders ON users.id = orders.user_id;"""),

"Python + SQLite": ("🐍", "Python работает с SQLite через модуль sqlite3: подключение к файлу базы, выполнение SQL-запросов и получение результатов.",
"""import sqlite3

conn = sqlite3.connect("app.db")
conn.execute("INSERT INTO users (name) VALUES (?)", ("Alex",))
conn.commit()
conn.close()"""),

# ---------- Раздел 20. Интернет и API ----------
"HTTP": ("🌐", "HTTP — протокол обмена данными между клиентом (браузером, ботом) и сервером в интернете.",
None),

"GET": ("📥", "GET-запрос используется для получения данных с сервера, например информации о погоде через API.",
"""import requests

response = requests.get("https://api.example.com/data")
print(response.json())"""),

"POST": ("📤", "POST-запрос используется для отправки данных на сервер, например при создании нового пользователя.",
"""import requests

response = requests.post(
    "https://api.example.com/users",
    json={"name": "Alex"}
)
print(response.status_code)"""),

"requests": ("📡", "requests — самая популярная библиотека Python для отправки HTTP-запросов и получения ответов от веб-сервисов.",
"""import requests

response = requests.get("https://api.github.com")
print(response.status_code)
print(response.json())"""),

"REST API": ("🌐", "REST API — архитектурный стиль веб-сервисов, где данные передаются через стандартные HTTP-методы (GET, POST, PUT, DELETE).",
None),

"headers": ("📋", "Заголовки (headers) HTTP-запроса передают дополнительную информацию — например, ключ авторизации или формат данных.",
"""import requests

headers = {"Authorization": "Bearer TOKEN"}
response = requests.get("https://api.example.com/data", headers=headers)"""),

"работа с API": ("🔌", "Работа с API обычно состоит из отправки запроса (requests), получения ответа в формате JSON и обработки этих данных в коде.",
"""import requests

response = requests.get("https://api.exchangerate-api.com/v4/latest/USD")
data = response.json()
print(data["rates"]["EUR"])"""),

# ---------- Раздел 21. Telegram-боты ----------
"Bot": ("🤖", "Класс Bot из aiogram представляет самого Telegram-бота и используется для отправки сообщений, фото и других действий.",
"""from aiogram import Bot

bot = Bot(token="ТВОЙ_ТОКЕН")"""),

"Dispatcher": ("🧭", "Dispatcher принимает обновления от Telegram (сообщения, нажатия кнопок) и распределяет их по нужным обработчикам.",
"""from aiogram import Dispatcher

dp = Dispatcher()"""),

"handlers": ("🎯", "Обработчики (handlers) — функции, которые срабатывают на определённые события: команду, текст сообщения или нажатие кнопки.",
"""@dp.message(F.text == "Привет")
async def handle_hello(message: Message):
    await message.answer("И тебе привет!")"""),

"Message": ("✉️", "Message — объект aiogram, представляющий сообщение пользователя: текст, отправителя, чат и другие данные.",
"""@dp.message()
async def echo(message: Message):
    await message.answer(f"Ты написал: {message.text}")"""),

"CallbackQuery": ("🔘", "CallbackQuery — объект, который приходит при нажатии на inline-кнопку под сообщением.",
"""@dp.callback_query(F.data == "yes")
async def handle_yes(callback: CallbackQuery):
    await callback.answer("Вы нажали Да!")"""),

"InlineKeyboard": ("⌨️", "InlineKeyboardMarkup создаёт кнопки, которые прикрепляются прямо под сообщением бота.",
"""from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Да", callback_data="yes")]
])"""),

"команды": ("⚡", "Команды Telegram-бота (например /start) обрабатываются через специальные фильтры вроде CommandStart().",
"""from aiogram.filters import CommandStart

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("Привет! Я бот.")"""),

"FSM": ("🔄", "FSM (Finite State Machine, конечный автомат) в aiogram позволяет вести пользователя через несколько шагов диалога, запоминая, на каком он этапе.",
"""from aiogram.fsm.state import State, StatesGroup

class Form(StatesGroup):
    name = State()
    age = State()"""),

"состояния": ("🧭", "Состояния FSM определяют, какого ответа бот ожидает от пользователя на текущем шаге диалога.",
"""@dp.message(Form.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Form.age)"""),

"SQLite + бот": ("💾", "SQLite отлично подходит для хранения данных Telegram-бота: пользователей, их прогресса, настроек — всё в одном файле.",
"""def touch_user(user_id):
    with sqlite3.connect("bot.db") as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,)
        )"""),

"API + бот": ("🔌", "Telegram-бот можно комбинировать с внешними API — например, показывать пользователю курс валют или погоду по запросу.",
"""@dp.message(F.text == "/weather")
async def weather(message: Message):
    response = requests.get("https://api.weather.example/current")
    await message.answer(response.json()["summary"])"""),

# ---------- Раздел 22. GUI ----------
"tkinter": ("🖥", "tkinter — встроенная в Python библиотека для создания графических окон приложений (GUI).",
"""import tkinter as tk

window = tk.Tk()
window.title("Моё приложение")
window.mainloop()"""),

"окна": ("🪟", "Окно — основа GUI-приложения: контейнер, в который добавляются кнопки, поля и текст.",
"""import tkinter as tk

window = tk.Tk()
window.geometry("300x200")
window.mainloop()"""),

"кнопки": ("🔘", "Виджет Button создаёт кликабельную кнопку, к которой привязывается функция-обработчик.",
"""import tkinter as tk

def on_click():
    print("Кнопка нажата!")

window = tk.Tk()
button = tk.Button(window, text="Нажми", command=on_click)
button.pack()
window.mainloop()"""),

"поля ввода": ("⌨️", "Виджет Entry создаёт текстовое поле, куда пользователь может вводить данные.",
"""import tkinter as tk

window = tk.Tk()
entry = tk.Entry(window)
entry.pack()
window.mainloop()"""),

"события": ("⚡", "GUI-программы реагируют на события: клики, нажатия клавиш, изменения текста — через привязанные функции-обработчики.",
"""button.bind("<Button-1>", lambda e: print("Клик!"))"""),

"создание приложений": ("🏗", "Полноценное GUI-приложение объединяет окно, виджеты (кнопки, поля) и обработчики событий в единый интерфейс.",
"""import tkinter as tk

def greet():
    label.config(text=f"Привет, {entry.get()}!")

window = tk.Tk()
entry = tk.Entry(window)
entry.pack()
tk.Button(window, text="Поздороваться", command=greet).pack()
label = tk.Label(window, text="")
label.pack()
window.mainloop()"""),

# ---------- Раздел 23. Игры ----------
"pygame": ("🎮", "pygame — библиотека для создания 2D-игр на Python: графика, звук, обработка ввода и игровой цикл.",
"""import pygame

pygame.init()
screen = pygame.display.set_mode((400, 300))
pygame.display.set_caption("Моя игра")"""),

"игровой цикл": ("🔁", "Игровой цикл — бесконечный цикл, который на каждой итерации обрабатывает ввод, обновляет состояние игры и перерисовывает экран.",
"""running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    pygame.display.flip()"""),

"движение": ("🏃", "Движение объекта в игре обычно реализуется изменением его координат (x, y) на каждой итерации игрового цикла.",
"""x, y = 100, 100
speed = 5
x += speed   # объект двигается вправо"""),

"столкновения": ("💥", "Столкновения между объектами проверяются через пересечение их прямоугольников (Rect) или дистанцию между координатами.",
"""player_rect = pygame.Rect(100, 100, 50, 50)
enemy_rect = pygame.Rect(120, 110, 50, 50)
if player_rect.colliderect(enemy_rect):
    print("Столкновение!")"""),

"изображения": ("🖼", "Изображения в pygame загружаются функцией image.load() и отрисовываются на экране методом blit().",
"""player_image = pygame.image.load("player.png")
screen.blit(player_image, (100, 100))"""),

"звук": ("🔊", "pygame умеет проигрывать звуковые эффекты и музыку через модуль pygame.mixer.",
"""pygame.mixer.init()
sound = pygame.mixer.Sound("jump.wav")
sound.play()"""),

"создание простой игры": ("🕹", "Простая игра на pygame состоит из инициализации, игрового цикла с обработкой ввода, обновлением объектов и отрисовкой кадра.",
"""import pygame
pygame.init()
screen = pygame.display.set_mode((400, 300))
clock = pygame.time.Clock()

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    screen.fill((0, 0, 0))
    pygame.display.flip()
    clock.tick(60)"""),

# ---------- Раздел 24. Тестирование ----------
"unittest": ("🧪", "unittest — встроенный в Python модуль для написания и запуска тестов, основанный на классах и методах assert.",
"""import unittest

class TestMath(unittest.TestCase):
    def test_addition(self):
        self.assertEqual(2 + 2, 4)

unittest.main()"""),

"pytest": ("✅", "pytest — популярная сторонняя библиотека для тестирования с более простым синтаксисом, чем у unittest.",
"""def add(a, b):
    return a + b

def test_add():
    assert add(2, 3) == 5"""),

"assert": ("☑️", "assert проверяет условие и вызывает ошибку AssertionError, если оно ложно — основа большинства тестов.",
"""def test_positive():
    assert 5 > 0
    assert (2 + 2) == 4"""),

"тестирование функций": ("🧪", "Тестирование функций проверяет, что при известных входных данных функция возвращает ожидаемый результат.",
"""def multiply(a, b):
    return a * b

def test_multiply():
    assert multiply(2, 3) == 6
    assert multiply(0, 5) == 0"""),

"фикстуры": ("🧰", "Фикстуры (fixtures) в pytest подготавливают данные или ресурсы для тестов, чтобы не дублировать код настройки.",
"""import pytest

@pytest.fixture
def sample_data():
    return [1, 2, 3]

def test_sum(sample_data):
    assert sum(sample_data) == 6"""),

"mock": ("🎭", "Mock (заглушка) подменяет реальный объект в тестах — полезно, если функция обращается к базе данных или внешнему API.",
"""from unittest.mock import Mock

api = Mock()
api.get_data.return_value = {"status": "ok"}
print(api.get_data())"""),

# ---------- Раздел 25. Работа с данными ----------
"NumPy": ("🔢", "NumPy предоставляет быстрые массивы (ndarray) и математические операции — основа для научных вычислений в Python.",
"""import numpy as np

arr = np.array([1, 2, 3, 4])
print(arr * 2)""",
"[2 4 6 8]"),

"Pandas": ("🐼", "Pandas — библиотека для анализа табличных данных: чтение CSV/Excel, фильтрация, группировка и агрегация.",
"""import pandas as pd

df = pd.DataFrame({"name": ["Alex", "Anna"], "age": [14, 15]})
print(df)"""),

"Matplotlib": ("📈", "Matplotlib строит графики: линии, столбцы, гистограммы — для визуализации данных.",
"""import matplotlib.pyplot as plt

plt.plot([1, 2, 3], [10, 20, 15])
plt.title("Мой график")
plt.savefig("chart.png")"""),

"таблицы": ("📋", "В Pandas данные хранятся в виде таблиц (DataFrame) со строками и именованными столбцами — как в Excel.",
"""import pandas as pd
df = pd.read_csv("data.csv")
print(df.head())"""),

"DataFrame": ("🗂", "DataFrame — основная структура данных в Pandas: двумерная таблица с индексами строк и названиями столбцов.",
"""import pandas as pd

df = pd.DataFrame({"город": ["Москва", "Казань"], "население": [12000000, 1300000]})
print(df["население"].mean())"""),

"графики": ("📊", "Графики помогают наглядно представить данные: тренды, сравнения, распределения значений.",
"""import matplotlib.pyplot as plt

plt.bar(["A", "B", "C"], [10, 20, 15])
plt.show()"""),

"анализ данных": ("📊", "Анализ данных — процесс изучения данных для выявления закономерностей, обычно с помощью Pandas, NumPy и Matplotlib.",
"""import pandas as pd

df = pd.read_csv("sales.csv")
print(df.groupby("category")["amount"].sum())"""),

# ---------- Раздел 26. Веб-разработка ----------
"Flask": ("🌶", "Flask — простой микрофреймворк для создания веб-сайтов и API на Python.",
"""from flask import Flask
app = Flask(__name__)

@app.route("/")
def home():
    return "Привет, мир!"

app.run(debug=True)"""),

"FastAPI": ("⚡", "FastAPI — современный асинхронный фреймворк для создания быстрых API с автоматической документацией.",
"""from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def home():
    return {"message": "Привет!"}"""),

"Django": ("🎸", "Django — полнофункциональный фреймворк «из коробки»: ORM, админ-панель, аутентификация и маршрутизация.",
"""django-admin startproject myproject
python manage.py runserver"""),

"маршруты": ("🛣", "Маршруты (роуты) связывают URL-адрес с функцией, которая обрабатывает запрос по этому адресу.",
"""@app.route("/about")
def about():
    return "О нас" """),

"запросы": ("📥", "Веб-фреймворки принимают HTTP-запросы от пользователя и возвращают ответ — HTML-страницу, JSON или файл.",
"""from flask import request

@app.route("/search")
def search():
    query = request.args.get("q")
    return f"Ищем: {query}" """),

"шаблоны": ("🖼", "Шаблоны (templates) позволяют вставлять данные Python в HTML-страницы, которые видит пользователь.",
"""from flask import render_template

@app.route("/")
def home():
    return render_template("index.html", name="Alex")"""),

"JSON API": ("🔌", "JSON API — веб-сервис, который принимает и возвращает данные в формате JSON, чаще всего для мобильных приложений и фронтенда.",
"""@app.get("/users/{id}")
def get_user(id: int):
    return {"id": id, "name": "Alex"}"""),

"базы данных": ("🗄", "Веб-приложения обычно хранят данные в базах данных (SQLite, PostgreSQL) и обращаются к ним через ORM, например SQLAlchemy или Django ORM.",
None),

# ---------- Раздел 27. Установка пакетов ----------
"venv": ("📦", "venv создаёт изолированное виртуальное окружение для проекта, чтобы зависимости разных проектов не конфликтовали.",
"""python -m venv venv
# Windows:
venv\\Scripts\\activate
# Linux/Mac:
source venv/bin/activate"""),

"requirements.txt": ("📄", "requirements.txt — файл со списком библиотек и их версий, нужных проекту, чтобы легко установить их все одной командой.",
"""pip install -r requirements.txt

# Сохранить текущие зависимости:
pip freeze > requirements.txt"""),

"PyPI": ("📦", "PyPI (Python Package Index) — официальный репозиторий, откуда pip скачивает библиотеки Python.",
None),

"установка библиотек": ("⬇️", "Библиотеки устанавливаются командой pip install и становятся доступны для импорта в коде.",
"""pip install requests
pip install aiogram
pip install pandas"""),

"виртуальные окружения": ("🧪", "Виртуальное окружение — отдельное «песочное» пространство с собственными библиотеками для конкретного проекта.",
"""python -m venv env
source env/bin/activate
pip install aiogram"""),

# ---------- Раздел 28. Git и GitHub ----------
"git add": ("➕", "git add добавляет изменённые файлы в «индекс» — область, откуда они попадут в следующий коммит.",
"""git add file.py
git add .   # добавить все изменённые файлы"""),

"git commit": ("💾", "git commit сохраняет добавленные изменения в историю проекта с описательным сообщением.",
"""git commit -m "Добавил новую функцию" """),

"git push": ("⬆️", "git push отправляет локальные коммиты на удалённый репозиторий, например на GitHub.",
"""git push origin main"""),

"git pull": ("⬇️", "git pull скачивает и применяет изменения из удалённого репозитория в локальный проект.",
"""git pull origin main"""),

"branches": ("🌿", "Ветки (branches) позволяют разрабатывать новую функциональность отдельно от основной версии проекта, не ломая её.",
"""git branch new-feature
git checkout new-feature
# или одной командой:
git checkout -b new-feature"""),

"merge": ("🔀", "git merge объединяет изменения из одной ветки в другую, например из feature-ветки в main.",
"""git checkout main
git merge new-feature"""),

"GitHub": ("🐙", "GitHub — сервис для хранения Git-репозиториев в интернете, совместной работы, отслеживания задач и публикации кода.",
None),

# ---------- Раздел 29. Безопасность ----------
"токены": ("🔑", "Токен — секретный ключ доступа к сервису, например токен Telegram-бота. Его нельзя публиковать в открытом коде.",
None),

".env": ("🗝", "Файл .env хранит секретные настройки (токены, пароли) отдельно от кода. Его добавляют в .gitignore, чтобы не попал в репозиторий.",
"""# .env
BOT_TOKEN=твой_секретный_токен
ADMIN_ID=123456789"""),

"переменные окружения": ("🌱", "Переменные окружения хранят конфиденциальные данные вне кода — их читают через os.getenv(), а не пишут напрямую в файл.",
"""import os
token = os.getenv("BOT_TOKEN")"""),

"пароли": ("🔒", "Пароли никогда не хранят в открытом виде — их шифруют (хешируют) специальными алгоритмами перед сохранением.",
"""import hashlib
hashed = hashlib.sha256("mypassword".encode()).hexdigest()"""),

"API keys": ("🗝", "API-ключи дают доступ к внешним сервисам. Их, как и токены, хранят в переменных окружения, а не в коде.",
None),

"основные ошибки безопасности": ("⚠️", "Частые ошибки: токены в открытом коде, отсутствие проверки ввода пользователя, хранение паролей без хеширования, публикация .env в Git.",
None),

# ---------- Раздел 30. Проекты ----------
"Калькулятор": ("🧮", "Хороший первый проект: консольный калькулятор, который считывает два числа и операцию, а затем выводит результат.",
"""a = float(input("Первое число: "))
op = input("Операция (+ - * /): ")
b = float(input("Второе число: "))

if op == "+":
    print(a + b)
elif op == "-":
    print(a - b)"""),

"Конвертер": ("🔄", "Конвертер валют или единиц измерения — хороший проект для практики работы с числами и, при желании, с внешним API курсов валют.",
None),

"Игра": ("🎮", "Простая текстовая игра (например, «угадай число») отлично закрепляет циклы, условия и работу со случайными числами.",
"""import random
number = random.randint(1, 100)
guess = int(input("Угадай число от 1 до 100: "))
if guess == number:
    print("Угадал!")"""),

"Telegram-бот": ("🤖", "Telegram-бот — практичный проект, объединяющий работу с API, обработку сообщений и, при желании, базу данных.",
None),

"Бот с SQLite": ("💾", "Бот с SQLite сохраняет данные пользователей и их действия в файл базы данных — так прогресс не теряется при перезапуске.",
None),

"Парсер": ("🕷", "Парсер собирает данные с веб-страниц с помощью requests и BeautifulSoup — например, цены товаров или новости.",
"""import requests
from bs4 import BeautifulSoup

html = requests.get("https://example.com").text
soup = BeautifulSoup(html, "html.parser")
print(soup.title.text)"""),

"Веб-приложение": ("🌐", "Веб-приложение на Flask или FastAPI объединяет маршруты, шаблоны и базу данных в единый рабочий сайт.",
None),

"Большой проект": ("🚀", "Большой проект сочетает несколько технологий сразу: например, Telegram-бот + база данных + внешнее API + аналитика.",
None),

# ---------- Раздел 31. Python и заработок ----------
"Telegram-боты": ("🤖", "Разработка Telegram-ботов — один из самых быстрых способов начать зарабатывать на Python: боты нужны магазинам, блогерам и небольшим компаниям.",
None),

"Парсеры": ("🕷", "Парсеры собирают данные с сайтов автоматически — востребованы для мониторинга цен, сбора вакансий, новостей и аналитики.",
None),

"Автоматизация": ("⚙️", "Автоматизация рутинных задач (обработка файлов, отчёты, рассылки) — частый заказ на фрилансе для Python-разработчиков.",
None),

"Web-разработка": ("🌐", "Веб-разработка на Flask, FastAPI или Django позволяет создавать сайты и API на заказ.",
None),

"Работа с API": ("🔌", "Многие заказы связаны с подключением к внешним API: платёжным системам, картам, соцсетям, магазинам.",
None),

"Портфолио": ("💼", "Портфолио из нескольких готовых проектов (бот, парсер, небольшой сайт) сильно повышает шансы получить первые заказы на фрилансе.",
None),

}
