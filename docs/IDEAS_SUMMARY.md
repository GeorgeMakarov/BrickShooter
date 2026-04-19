# v2 Extension Ideas — Short List

A trimmed-down list of ideas for extending BrickShooter v2.
The Russian version below is meant to be forwarded to dad for feedback.

---

## English

### Special bricks (reward bigger matches)
- **4-match → Bomb brick.** One random brick in the launch zone turns into a bomb. When it is later fired and lands, it clears the 8 neighbouring cells.
- **5-match → Wildcard brick.** One random brick in the launch zone turns into a wildcard that matches any colour when it forms a group.
- **6-match → Colour bomb.** One launcher brick becomes a colour bomb; firing it removes every brick of that colour from the play area.
- **7-match → Row/column blaster.** One launcher brick becomes a blaster; firing it clears the entire row and column it stops in.

### More challenge
- **Steeper obstacle curve.** Instead of `level + 1` obstacles, grow faster (e.g. `level * 2`) so middle levels become meaningfully harder.
- **Stone bricks.** Permanent walls for the level — cannot be matched and cannot be moved. Level ends when all non-stone cells are clear. Only counterplay is a bomb or blaster (from the "special bricks" ideas); without those, the player has to route shots around them.
- **Durable bricks (HP ×2, ×3).** Bricks with a counter on their face; they must be matched in a group N times before they disappear. Every match decreases the counter.
- *(lower priority)* Shot-count limit per level, mini-timer on top of an already-placed obstacle, or a periodic "intruder" brick that drops into the play area if the player stalls.

### Game modes
- **Campaign.** Hand-designed levels with fixed starting layouts, star rating per level.
- **Daily challenge.** One seed per day, shared leaderboard.
- **Endless.** Current mode, but obstacles keep being sprinkled in while playing.
- **Single-shot puzzles.** Pre-set board, clear everything in exactly one shot.

### Meta / profile
- **Stats page.** Per-player totals: games played, levels cleared, best combo, favourite colour.
- **Scoreboard time filters.** Today / this week / all-time views.
- **Replay.** Store the shot sequence of a high-score run and let it play back.
- **Avatars / player colour.** Small cosmetic flourish next to the name.

---

## Для отправки папе (Russian)

### Специальные кирпичи (награда за большие группы)
- **Группа из 4 → Кирпич-бомба.** Один случайный кирпич в зоне запуска превращается в бомбу. Когда его выстрелят и он приземлится — сносит 8 соседних клеток.
- **Группа из 5 → Универсальный кирпич (wildcard).** Один кирпич в зоне запуска становится «джокером» — совпадает с любым цветом при образовании группы.
- **Группа из 6 → Цветная бомба.** Один кирпич в зоне запуска становится цветной бомбой; при выстреле убирает все кирпичи того цвета с игрового поля.
- **Группа из 7 → Разрушитель ряда и колонны.** Один кирпич в зоне запуска становится «лучом»; при выстреле очищает ряд и колонну, в которых он остановился.

### Усложнение игры
- **Круче кривая препятствий.** Вместо `уровень + 1` препятствий — расти быстрее (например, `уровень × 2`), чтобы средние уровни реально ощущались труднее.
- **Каменные кирпичи.** Постоянные «стены» на уровне — не матчатся и не двигаются. Уровень считается пройденным, когда в игровом поле не осталось не-каменных кирпичей. Единственный способ убрать камень — эффект бомбы или луча (из раздела «специальные кирпичи»). Без них игрок просто обходит камни выстрелами.
- **«Прочные» кирпичи (HP ×2, ×3).** Кирпич с цифрой на лице; чтобы он исчез, его нужно включить в группу N раз. Каждое попадание в группу уменьшает счётчик.
- *(менее приоритетное)* Лимит выстрелов на уровень, мини-таймер на уже стоящем препятствии, периодический «незваный» кирпич, который падает на поле, если игрок долго думает.

### Режимы игры
- **Кампания.** Заранее сделанные уровни с фиксированной стартовой раскладкой, оценка в звёздах за уровень.
- **Ежедневный челлендж.** Один сид на день, общий лидерборд.
- **Бесконечный режим.** Как сейчас, но на поле периодически досыпаются новые препятствия.
- **Пазлы в один выстрел.** Подготовленная расстановка — очистить всё поле ровно одним выстрелом.

### Мета / профиль
- **Страница статистики.** По игроку: сыграно игр, пройдено уровней, лучшая серия (combo), любимый цвет.
- **Фильтры таблицы рекордов.** Сегодня / эта неделя / за всё время.
- **Реплей.** Сохранять последовательность выстрелов рекордной игры и воспроизводить.
- **Аватары / цвет игрока.** Небольшое косметическое украшение рядом с именем.
