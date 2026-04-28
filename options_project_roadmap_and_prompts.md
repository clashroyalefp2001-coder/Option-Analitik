# Roadmap и промты для проекта по торговле опционами

## Как использовать документ
Этот документ объединяет два прикладных блока для запуска проекта по торговле американскими опционами на акции на MOEX: подробный roadmap на 8–12 недель и набор готовых промтов для AI-ассистента по ключевым модулям системы.[web:93][web:94] Логика roadmap строится вокруг постепенного перехода от исследования гипотез и сборки данных к walk-forward валидации, paper trading и production-мониторингу, потому что в квантовых стратегиях именно поэтапная проверка на truly unseen data лучше защищает от переобучения, чем один статичный backtest.[web:89][web:93][web:94]

В документе сознательно разделены research, engineering и trading-governance задачи, поскольку для опционной торговли недостаточно одной “хорошей модели”: нужны валидный pipeline данных, реалистичный backtest, фильтры ликвидности и регулярный drift-monitoring после запуска.[web:84][web:87][web:99] Для проекта с коротким горизонтом удержания и дневной частотой пересчёта это особенно важно, так как edge может исчезать быстрее, чем деградация станет заметна по итоговому PnL без промежуточных контрольных метрик.[web:87][web:104]

---

# Вариант 1 — Roadmap на 8–12 недель

## Общая логика проекта
Цель проекта — не просто оценивать опцион, а строить систему поиска и отбора сделок, где structural pricing-модель создаёт fair-value baseline, ML-модель ранжирует сделки по ожидаемому edge, а слой risk/execution отбрасывает неликвидные и неисполняемые сигналы.[web:102][web:97][web:100] Поэтому roadmap ниже организован так, чтобы каждый следующий этап начинался только после того, как предыдущий даёт проверяемый deliverable: чистые данные, рабочий pricing engine, baseline model, walk-forward результаты и мониторинговый контур.[web:93][web:94][web:99]

## План на 10 недель
Это базовая версия, которая хорошо укладывается в окно 8–12 недель. Если команда маленькая, часть этапов можно сдвигать на 1–2 недели; если команда сильная, некоторые инженерные работы можно вести параллельно.[web:87][web:93]

| Неделя | Этап | Основные задачи | Deliverables |
|---|---|---|---|
| 1 | Постановка гипотез | Зафиксировать universe инструментов, выбрать ликвидные underlying и серии, определить горизонт удержания, целевую метрику прибыли, baseline costs model | Research memo по гипотезам, список инструментов, KPI/метрики проекта |
| 2 | Data inventory | Подключить источники MOEX/поставщика данных, собрать структуру таблиц по опционам, underlying, IV, стакану, OI, объёмам, событиям | Data dictionary, схема хранилища, список обязательных полей |
| 3 | Data pipeline v1 | Реализовать загрузку, очистку, time alignment, sanity checks, хранение исторических снапшотов и mid/bid/ask | ETL v1, тесты качества данных, первый очищенный датасет |
| 4 | Pricing layer v1 | Реализовать биномиальное дерево для американских опционов, пересчёт Greeks, mispricing, early-exercise premium | Pricing module v1, unit tests, таблица baseline features |
| 5 | Feature engineering | Добавить IV features, liquidity features, order book imbalance, realized vol, moneyness, residual features | Feature store v1, спецификация всех признаков |
| 6 | ML baseline | Обучить LightGBM/XGBoost baseline на future trade return или profitable-trade label, сделать feature importance и первичную калибровку | ML baseline report, сохранённая модель, baseline metrics |
| 7 | Backtest engine | Реализовать costs-aware backtest: bid/ask execution, slippage proxy, hold rules, exits, portfolio constraints | Backtest engine v1, отчёт по IS/OOS, логи сделок |
| 8 | Walk-forward validation | Прогнать rolling walk-forward и hold-out, разделить результаты по режимам рынка и ликвидности | Walk-forward report, regime diagnostics, fail/pass decision |
| 9 | Risk & execution layer | Добавить hard/soft liquidity gates, position sizing, Greek limits, event filters, kill-switch rules | Risk policy v1, execution filter module |
| 10 | Paper trading & monitoring | Запустить daily pipeline без реальных денег, вести signal log, drift log, hit-rate log, alerts | Paper-trading dashboard, monitoring spec, launch decision memo |

## Если делать 8 недель
Сжатая версия возможна, если отказаться от избыточной архитектуры на старте и оставить только один pricing engine, один baseline ML-алгоритм и один тип backtest.[web:93][web:94] В таком варианте недели 2–3 объединяются в единый блок по данным, недели 4–5 — в блок pricing + features, а недели 6–8 — в baseline model, walk-forward и paper trading.[web:89][web:93]

Сжатый план выглядит так:
- Недели 1–2: hypotheses + data pipeline.[web:93]
- Недели 3–4: pricing + features.[web:102]
- Неделя 5: ML baseline.[web:89]
- Неделя 6: costs-aware backtest.[web:93]
- Неделя 7: walk-forward + hold-out.[web:94]
- Неделя 8: paper trading + monitoring setup.[web:84][web:87]

## Если делать 12 недель
Расширенная версия имеет смысл, если сразу хочешь построить не только baseline, но и production-ready контур с uncertainty filter, ансамблями и развёрнутым monitoring stack.[web:84][web:99] Тогда после недели 10 добавляются ещё 2 недели на улучшение модели и контроль устойчивости.[web:87][web:104]

Дополнительные недели:
- Неделя 11: ансамбль моделей, например LightGBM + MLP или LightGBM + GP для uncertainty-aware filtering.[web:99][web:102]
- Неделя 12: production hardening — drift alerts, retraining scheduler, runbook инцидентов, контроль деградации feature distribution через PSI/KL и performance triggers.[web:84][web:87][web:99]

## Этапы подробно

### Недели 1–2: гипотезы и данные
На первом этапе проект должен ответить на вопрос, **где именно может жить альфа**: в residual mispricing, в краткосрочной деформации IV surface, в imbalance стакана, в post-event mean reversion или в комбинации этих факторов.[web:97][web:100][web:102] Без этого команда быстро сваливается в бессистемное “натаскивание модели на всё подряд”, а это почти всегда ведёт к leakage и слабой вневыборочной устойчивости.[web:93][web:94]

Задачи этапа:
- определить universe: underlying, expiries, strikes, минимальный уровень ликвидности;
- решить, что является execution price: ask для покупки, bid для продажи, плюс комиссия;
- зафиксировать основной target, например 5-дневный или 10-дневный net return after costs;
- собрать data dictionary и правила time alignment между underlying, опционами и стаканом.[web:97][web:102]

Deliverables:
- список торгуемых серий;
- описание таргета;
- схема таблиц и ETL;
- правила фильтрации «мёртвых» серий и аномальных записей.[web:87]

### Недели 3–4: pricing и признаки
На этом этапе появляется structural layer, который даёт не торговый сигнал сам по себе, а объяснимый набор признаков: fair value, Greeks, early exercise premium, residual mispricing и производные IV-метрики.[web:102] Это важно, потому что ML-модель обычно сильнее работает на residual-сигнале поверх fair-value baseline, чем на попытке предсказывать цену опциона напрямую.[web:102]

Задачи этапа:
- реализовать биномиальное дерево для американских опционов;
- проверить sanity constraints по intrinsic value и monotonicity;
- вычислить IV features: skew, slope, curvature, IV/RV ratio;
- собрать liquidity features: spread, depth, imbalance, OI change, volume/OI.[web:97][web:100][web:102]

Deliverables:
- pricing module v1;
- таблица признаков по каждой серии и дате;
- baseline residual dataset для ML.[web:102]

### Недели 5–6: baseline ML и первый backtest
Здесь запускается первая практическая alpha-модель. В большинстве торговых задач лучше начинать с интерпретируемого и быстрого бустинга, потому что он быстрее показывает, есть ли вообще signal content в данных, чем тяжёлая нейросеть.[web:93][web:94] Сразу после обучения нужен backtest, который учитывает спред, costs и фактическую исполнимость, иначе результат будет завышен.[web:93]

Задачи этапа:
- обучить LightGBM/XGBoost baseline на label profitable trade или future net return;
- проверить важность признаков и стабильность importance между фолдами;
- реализовать position entry/exit rules и hold horizon;
- включить costs model и slippage proxy в backtest.[web:93][web:102]

Deliverables:
- baseline model artifact;
- таблица feature importance;
- backtest report v1 с equity curve, Sharpe, hit rate, drawdown.[web:89][web:93]

### Недели 7–8: walk-forward и режимы рынка
Walk-forward analysis нужен как обязательный барьер между красивым backtest и реальной торговлей, потому что rolling out-of-sample лучше показывает, переживает ли стратегия смену режима рынка.[web:89][web:93][web:94] Для опционной торговли это особенно важно из-за нестабильности ликвидности, волатильности и post-event поведения implied volatility.[web:102]

Задачи этапа:
- настроить rolling train/validation/test windows;
- провести hold-out test на полностью нетронутом отрезке;
- разрезать результаты по спокойным, волатильным и стрессовым периодам;
- проверить устойчивость метрик и turnover-adjusted profitability.[web:89][web:93][web:94]

Deliverables:
- walk-forward report;
- regime report;
- список гипотез/признаков, которые стоит убрать или усилить.[web:89][web:94]

### Недели 9–10: риск, paper trading и monitoring
После того как доказан baseline edge, проект должен перейти к управляемому production-процессу: сигналы, риск-фильтры, логирование, drift detection и paper trading без капитала.[web:84][web:87][web:99] Это необходимый этап, потому что даже хорошая OOS-модель может разрушиться из-за деградации data feed, смены ликвидности или изменения связи между features и target.[web:84][web:104]

Задачи этапа:
- внедрить hard filters по spread, OI, depth, event dates;
- реализовать position sizing и греческие лимиты;
- настроить daily monitoring по data drift и model performance;
- запустить paper trading и собирать signal vs realized outcome logs.[web:84][web:87][web:99]

Deliverables:
- risk policy document;
- monitoring dashboard spec;
- paper trading journal;
- go/no-go memo на real money launch.[web:84][web:87]

## Управление проектом
Проект лучше вести по спринтам в 1 неделю, где на каждый модуль есть owner, критерий готовности и минимальный measurable outcome.[web:87][web:99] Удобная логика управления:
- Research board: гипотезы, проверки, OOS решения;
- Engineering board: data, pricing, backtest, deployment;
- Trading board: risk rules, capital allocation, live readiness.[web:84][web:87]

Для каждого спринта полезно фиксировать:
- что проверяем;
- какие данные нужны;
- какая метрика pass/fail;
- что делаем, если гипотеза не проходит;
- какие артефакты должны остаться после спринта.[web:93][web:94]

## Критерии перехода в live
Переходить к реальным деньгам имеет смысл только если одновременно выполнены несколько условий:
- walk-forward даёт устойчивую OOS-прибыльность, а не один удачный сегмент истории;[web:89][web:93]
- стратегия положительна после realistic costs;[web:94]
- есть risk filters и kill-switches;[web:84]
- есть paper trading период с подтверждением исполнимости;[web:87]
- настроен drift monitoring и регламент retraining.[web:84][web:99]

---

# Вариант 2 — Готовые промты для AI-ассистента

## Как использовать эти промты
Ниже — промты, которые можно давать AI-ассистенту по отдельным модулям проекта. Они сформулированы так, чтобы ассистент не уходил в абстракцию, а выдавал архитектуру, код, тесты, критерии качества и production-ready артефакты.[web:87][web:99] Во всех промтах заложена логика торговли, а не академического price fitting: модель должна работать на future trade return, учитывать liquidity/execution и проходить walk-forward валидацию.[web:89][web:93][web:94]

## Prompt 1 — Data module
```text
Ты — senior quant data engineer. Помоги спроектировать и реализовать модуль data pipeline для проекта торговли американскими опционами на акции на MOEX.

Контекст проекта:
- Цель не в академической оценке опциона, а в поиске торговой альфы.
- Горизонт удержания: 2 недели – 1 месяц.
- Частота решений: 1 раз в день.
- Доступные данные: цены underlying, опционы, implied volatility, order book, объёмы, open interest, дивиденды, корпоративные события.

Что нужно сделать:
1. Спроектировать структуру хранилища данных.
2. Описать таблицы: underlying_prices, option_quotes, order_book_snapshots, iv_surface, corporate_actions, rates.
3. Предложить ETL pipeline: загрузка, очистка, дедупликация, time alignment, sanity checks.
4. Предложить правила фильтрации неликвидных и “мёртвых” серий.
5. Написать Python-структуру проекта: fetcher.py, cleaner.py, validator.py, features_input_builder.py.
6. Добавить unit tests для критических проверок качества данных.
7. Выдать итог в виде:
   - архитектуры модуля,
   - SQL/Pandas-схем,
   - чек-листа валидации,
   - примеров кода.

Важные ограничения:
- Нельзя использовать future leakage.
- Нужно разделять quote time и feature availability time.
- Bid/ask важнее mid-price, если речь про торговлю.
- Все поля должны быть пригодны для дальнейшего walk-forward backtest.

Фокусируйся на production-grade реализации.
```

## Prompt 2 — Pricing module
```text
Ты — senior quant developer по опционам. Помоги разработать pricing module для американских опционов на акции для проекта alpha-trading на MOEX.

Контекст:
- Базовый pricing engine нужен как structural layer, а не как финальный торговый сигнал.
- Основная цель — получить fair value, Greeks, early exercise premium и residual mispricing features для ML-модели.
- Горизонт сделок: 2 недели – 1 месяц.

Что нужно сделать:
1. Реализовать биномиальную модель (CRR или Leisen-Reimer) для американских опционов.
2. Опционально предложить LSMC-расширение как вторую модель.
3. Определить входы: S, K, T, r, sigma, dividends, option_type.
4. Определить выходы: fair_value, delta, gamma, vega, theta, rho, early_exercise_premium, residual_to_mid, residual_to_bid_ask.
5. Добавить sanity tests:
   - price >= intrinsic value,
   - monotonicity,
   - адекватность Greeks,
   - устойчивость на коротких сроках до экспирации.
6. Подготовить Python-код модуля и примеры использования в feature pipeline.
7. Отдельно объяснить, какие величины лучше передавать в ML как признаки.

Важно:
- Не ограничиваться только Black-Scholes.
- Учитывать, что рынок может быть неликвидным, поэтому residual к bid/ask важнее residual к mid.
- Код должен быть пригоден для пакетного расчёта по многим сериям.
```

## Prompt 3 — ML / Alpha-Ranking module
```text
Ты — senior quant ML researcher. Помоги разработать ML-модуль для alpha/ranking в торговле американскими опционами на акции.

Главная цель:
Предсказывать не абсолютную цену опциона, а будущую доходность сделки с учётом implied volatility, кривизны IV surface, order book imbalance, ликвидности, spread и движения underlying.

Контекст:
- Слой 1 уже даёт fair value и Greeks.
- Слой 2 должен оценивать expected trade edge или probability of profitable trade.
- Частота решений дневная.
- Горизонт удержания 5–20 торговых дней.

Что нужно сделать:
1. Предложить target definitions:
   - future net return after costs,
   - profitable trade label,
   - expected edge.
2. Спроектировать feature groups:
   - structural (fair value, Greeks, residuals),
   - volatility surface,
   - liquidity/order book,
   - underlying dynamics,
   - event/calendar.
3. Предложить baseline model (LightGBM/XGBoost) и advanced model (MLP/LSTM/GP).
4. Описать схему walk-forward обучения и hyperparameter tuning без leakage.
5. Предложить метрики: net Sharpe, hit rate, max drawdown, turnover-adjusted PnL, regime stability.
6. Подготовить код-скелет training pipeline.
7. Добавить советы по interpretability: feature importance, SHAP, uncertainty filter.

Важно:
- Не оптимизировать только MSE по цене.
- Нужно думать как trader, а не как academic forecaster.
- Обязательно учитывать class imbalance, regime shifts и overfitting risk.
```

## Prompt 4 — Backtest module
```text
Ты — senior quant backtesting engineer. Помоги спроектировать реалистичный backtest engine для стратегии торговли американскими опционами на акции на MOEX.

Контекст:
- Модель предсказывает expected trade edge или profitable trade probability.
- Сделки совершаются не по mid, а по реалистичной цене исполнения через bid/ask.
- Горизонт удержания 5–20 торговых дней.

Что нужно сделать:
1. Спроектировать backtest engine с поддержкой:
   - entry/exit rules,
   - holding period,
   - transaction costs,
   - slippage proxy,
   - partial fills / liquidity constraints (если возможно).
2. Реализовать walk-forward validation.
3. Разделить IS, validation, OOS и final untouched hold-out.
4. Добавить regime segmentation: calm / volatile / stress.
5. Подготовить метрики:
   - equity curve,
   - annualised Sharpe,
   - drawdown,
   - hit rate,
   - average holding return,
   - tail loss,
   - turnover-adjusted return.
6. Добавить protection against backtest overstatement.
7. Подготовить Python-code skeleton модуля.

Важно:
- Нельзя использовать будущую информацию при генерации сигнала.
- Backtest должен быть пригоден для последующего paper trading.
- Нужно показать, как логировать каждую сделку и каждое решение модели.
```

## Prompt 5 — Risk / Execution module
```text
Ты — senior quant risk engineer. Помоги разработать risk and execution layer для проекта торговли американскими опционами на акции.

Контекст:
- Есть alpha model, которая ранжирует сделки.
- Нужно не допустить в торговлю слабые, неликвидные или чрезмерно рискованные сигналы.

Что нужно сделать:
1. Предложить hard filters:
   - spread threshold,
   - minimum open interest,
   - minimum daily volume,
   - DTE bounds,
   - event blackout windows.
2. Предложить soft filters:
   - predicted edge > execution cost,
   - confidence threshold,
   - regime-aware size reduction.
3. Спроектировать position sizing:
   - fixed risk budget,
   - fractional Kelly,
   - Greek exposure caps.
4. Описать exit logic:
   - stop loss,
   - take profit,
   - time exit,
   - signal flip.
5. Подготовить правила portfolio-level control:
   - max delta/gamma/vega exposure,
   - concentration limits,
   - daily loss limit,
   - kill switch.
6. Выдать псевдокод и Python skeleton.

Важно:
- Думай не как academic optimizer, а как risk manager реальной стратегии.
- Все правила должны быть пригодны для автоматизации.
```

## Prompt 6 — Monitoring / MLOps module
```text
Ты — senior MLOps engineer для торговых ML-систем. Помоги построить monitoring и retraining framework для проекта торговли американскими опционами.

Контекст:
- Есть data pipeline, pricing layer, ML-model, backtest и risk filters.
- Модель работает на дневной частоте и должна регулярно переоцениваться.
- Нужно отслеживать data drift, model drift и execution drift.

Что нужно сделать:
1. Спроектировать monitoring dashboard для следующих блоков:
   - data quality,
   - feature drift,
   - prediction quality,
   - realized PnL,
   - signal hit rate,
   - execution slippage.
2. Предложить drift metrics:
   - PSI,
   - KL divergence,
   - rolling performance degradation,
   - stability of feature importance.
3. Описать alerting rules и severity levels.
4. Описать retraining policy:
   - daily recalc,
   - weekly validation,
   - monthly full retrain,
   - emergency retrain on severe drift.
5. Описать incident runbook:
   - что делать при деградации data feed,
   - что делать при резком ухудшении model performance,
   - что делать при market regime break.
6. Подготовить архитектуру логирования и storage слоёв.

Важно:
- Нужен именно production monitoring для торговли, а не формальный MLOps ради галочки.
- Monitoring должен помогать принять решение: continue / reduce size / stop / retrain.
```

## Prompt 7 — Главный orchestration prompt
```text
Ты — lead quant architect проекта по торговле американскими опционами на акции на MOEX.

Твоя задача — координировать разработку трёхслойной системы:
1. Базовый pricing-движок для fair value и Greeks.
2. ML alpha/ranking layer для предсказания будущей доходности сделки.
3. Risk/execution layer для отбора, позиционирования и контроля риска.

Главная идея проекта:
Нельзя предсказывать только “честную цену” опциона. Нужно предсказывать будущую торговую доходность сделки с учётом implied volatility, кривизны поверхности IV, order book imbalance, liquidity conditions, spread, costs и движения underlying.

Работай как технический руководитель.
Для каждого нового модуля выдавай:
- архитектуру,
- список задач,
- структуру файлов,
- Python-скелет,
- тесты,
- критерии готовности,
- риски и узкие места.

Приоритеты:
- production practicality,
- walk-forward robustness,
- отсутствие leakage,
- risk-aware design,
- interpretability before complexity.

Если есть выбор между красивой сложной моделью и устойчивой практичной моделью — выбирай устойчивую практичную.
```

## Как лучше использовать набор промтов
Практически лучше всего запускать их не все сразу, а по мере зрелости проекта: сначала data, потом pricing, потом ML, затем backtest, risk и monitoring.[web:93][web:94] Такой порядок соответствует лучшим практикам walk-forward research process, где прежде чем усиливать модель, нужно доказать, что данные, симуляция исполнения и OOS-валидация вообще отражают реальность.[web:89][web:93]

Если AI-ассистент силён в коде, полезно давать ему сначала orchestration prompt, а затем модульный prompt как конкретный task order, чтобы он не терял системный контекст.[web:87][web:99] Это снижает риск того, что assistant начнёт писать локально красивый код, который потом не стыкуется с общей архитектурой проекта.[web:87]
