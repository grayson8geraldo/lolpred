# LoL Match Predictor

Система прогнозирования матчей профессионального League of Legends. Веб-интерфейс + CLI.

Прогнозирует: победителя матча, количество карт (BO3/BO5), продолжительность игры, первую вышку, первого дракона, первую кровь, первого вестника.

## Установка с нуля

### 1. Системные требования

- Python 3.10+
- pip
- git

#### Ubuntu / Debian
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git
```

#### macOS
```bash
brew install python3 git
```

#### Windows
Скачать и установить:
- Python 3.10+: https://www.python.org/downloads/ (при установке отметить "Add to PATH")
- Git: https://git-scm.com/downloads

### 2. Клонирование репозитория

```bash
git clone https://github.com/grayson8geraldo/lolpred.git
cd lolpred
```

### 3. Создание виртуального окружения

```bash
python3 -m venv venv
source venv/bin/activate        # Linux / macOS
# venv\Scripts\activate         # Windows
```

### 4. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 5. Загрузка данных

**Вариант A: Скачать реальные данные из Oracle's Elixir**
```bash
python main.py download
```
Скачивает CSV за 2024-2025 из [Oracle's Elixir](https://oracleselixir.com/tools/downloads).

Для дополнительных годов:
```bash
python main.py download --years 2022 2023 2024 2025
```

**Вариант B: Сгенерировать тестовые данные**
```bash
python main.py generate
```
Генерирует симулированные данные на основе реальных составов команд для быстрого тестирования.

### 6. Запуск

#### Веб-интерфейс (рекомендуется)
```bash
python web.py
```
Откройте http://localhost:5000 в браузере.

#### Командная строка (CLI)
```bash
python main.py predict "T1" "Gen.G" --format BO3
python main.py rankings --region LCK
python main.py stats "T1"
```

## Веб-интерфейс

Запуск:
```bash
python web.py
```

Страницы:
- **/** — Форма прогнозирования матча (выбор команд, формата, быстрые примеры)
- **/predict** — Результат прогноза (победитель, карты, длительность, первые объекты)
- **/rankings** — Рейтинг Elo по регионам (LCK, LPL, LEC, LCS, PCS)
- **/rankings?region=LCK** — Рейтинг конкретного региона
- **/team/{name}** — Детальная статистика команды
- **/api/teams** — JSON API списка команд
- **/api/teams?region=LPL** — JSON API с фильтром по региону

Функции:
- Темная тема в стиле киберспорта
- Фильтр команд по региону
- Визуальные шкалы вероятностей
- Детальная статистика каждой команды
- Адаптивный дизайн (мобильные + десктоп)

## CLI

```bash
# Прогноз матча
python main.py predict "T1" "Gen.G" --format BO3
python main.py predict "Bilibili Gaming" "Top Esports" --format BO5
python main.py predict "G2 Esports" "Fnatic" --format BO1

# Рейтинги
python main.py rankings                    # Глобальный топ 30
python main.py rankings --region LCK       # Только LCK

# Список команд
python main.py teams                       # Все команды
python main.py teams --region LPL          # Только LPL

# Статистика команды
python main.py stats "T1"
python main.py stats "Gen.G"
```

## Источники данных

**Основной: [Oracle's Elixir](https://oracleselixir.com/tools/downloads)**
- Бесплатные CSV, 100+ полей на игру, обновляются ежедневно
- Все крупные лиги с 2014 по сегодня
- Поля: result, gamelength, firsttower, firstdragon, firstblood, firstherald, firstbaron, golddiffat10/15, kills/deaths/assists, объекты

**Дополнительные:**
- [gol.gg](https://gol.gg) — Статистика турниров, команд, игроков. URL-паттерны:
  - Турнир: `gol.gg/tournament/tournament-stats/{NAME}/`
  - Команда: `gol.gg/teams/team-stats/{ID}/split-ALL/tournament-{NAME}/`
  - Игра: `gol.gg/game/stats/{GAME_ID}/page-game/`
  - Список турниров: `gol.gg/tournament/list/`
- [Leaguepedia](https://lol.fandom.com) — Вики с API для матчей
- [LoL Esports Data Portal](https://grid.gg/get-league-of-legends/) — Официальные данные Riot через GRID/Bayes

## Регионы (Топ 5)

| Регион | League IDs | Описание |
|--------|-----------|----------|
| LCK | LCK | Корея |
| LPL | LPL | Китай |
| LEC | LEC | Европа |
| LCS | LCS, LTA, LTA North | Северная Америка |
| PCS | PCS | Тихоокеанский регион |

## Прогнозы

| # | Тип | Метод |
|---|-----|-------|
| 1 | Победитель матча | Elo + корректировка по форме, экономике, KDA |
| 2 | Количество карт (BO3/BO5) | Биномиальная модель от per-game вероятности |
| 3 | Продолжительность карты | Среднее двух команд + over/under (логистика, std=4.5 мин) |
| 4 | Первая вышка | Сравнение % забора первой вышки |
| 5 | Первый дракон | Сравнение % забора первого дракона |
| 6 | Первая кровь | Сравнение % первой крови |
| 7 | Первый вестник | Сравнение % забора первого вестника |

## Стратегия прогнозирования

### Elo-рейтинг
- Начальный рейтинг: 1500
- K-фактор: 32
- Регрессия к среднему между сезонами: 25%
- Обновляется после каждой игры (не серии)

### Корректировка вероятности победы
Базовая вероятность по Elo корректируется:
- **Текущая форма** (винрейт за последние 15 игр) — вес 15%
- **Ранняя экономика** (avg gold diff @10 min) — вес до 10%
- **K/D ratio** — вес 5%

### Модель количества карт
Биномиальное распределение:
- BO3: P(2-0) = p^2, P(2-1) = 2pqp, P(0-2) = q^2, P(1-2) = 2pqq
- BO5: Отрицательное биномиальное (первый до 3 побед)

### Модель продолжительности
- Прогноз = среднее avg game length обеих команд
- Over/under через логистическую аппроксимацию (std ~4.5 мин)

### Первые объекты
- Сравнение исторических % забора каждого объекта
- Нормализация для head-to-head вероятности

## Используемые поля данных

Из Oracle's Elixir CSV (строки с position='team'):

| Поле | Тип | Описание |
|------|-----|----------|
| result | 0/1 | Победа/поражение |
| gamelength | int | Длительность в секундах |
| firsttower | 0/1 | Первая вышка |
| firstdragon | 0/1 | Первый дракон |
| firstblood | 0/1 | Первая кровь |
| firstherald | 0/1 | Первый вестник |
| firstbaron | 0/1 | Первый барон |
| golddiffat10 | int | Разница золота на 10 мин |
| golddiffat15 | int | Разница золота на 15 мин |
| kills/deaths/assists | int | Убийства/смерти/ассисты |
| dragons/towers/barons | int | Количество объектов |

## Структура проекта

```
lolpred/
├── main.py              # CLI
├── web.py               # Flask веб-приложение
├── config.py            # Конфигурация (URL, регионы, параметры Elo)
├── requirements.txt     # Зависимости Python
├── templates/           # HTML шаблоны (Jinja2)
│   ├── base.html        # Базовый шаблон (навигация, стили)
│   ├── index.html       # Главная (форма прогноза)
│   ├── result.html      # Результат прогноза
│   ├── rankings.html    # Рейтинги команд
│   └── team.html        # Статистика команды
├── data/                # CSV данные (gitignored)
└── src/
    ├── data_loader.py   # Загрузка/парсинг данных Oracle's Elixir
    ├── features.py      # Elo система + скользящая статистика
    ├── predictor.py      # Движок прогнозирования
    ├── display.py       # Форматирование для терминала
    └── sample_data.py   # Генератор тестовых данных
```
