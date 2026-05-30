# 過去価格取得とグリッドバックテスト実装

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

この計画はリポジトリ直下の `PLANS.md` に従って維持する。作業ディレクトリは `C:\Users\Hodaka\Downloads\div\hyperbot` とする。

## Purpose / Big Picture

この変更で、ユーザーはグリッド Bot の設定を決める前に、指定ティッカーの過去価格を指定分足と指定期間で取得できるようになる。さらに、取得済みのローソク足データに対して、グリッド上限、下限、グリッド本数、グリッド間隔、使用するドル金額を指定し、その設定なら過去どの程度の損益になったかをローカルで検証できる。どちらの機能も Bot 本体から切り離して単独実行できるため、戦略検討用の小さな CLI と import 可能な Python モジュールとして使える。

## Progress

- [x] (2026-05-30 19:35 JST) 既存の Phase 1 実装と SDK の `Info.candles_snapshot(name, interval, startTime, endTime)` シグネチャを確認した。
- [x] (2026-05-30 19:36 JST) `codex/historical-backtest` ブランチを作成した。
- [x] (2026-05-30 19:43 JST) TDD で過去価格取得のパラメータ変換、ローソク足正規化、CSV 出力のテストを追加し、`ModuleNotFoundError` で失敗することを確認した。
- [x] (2026-05-30 19:43 JST) TDD でグリッドバックテストの設定検証、売買シミュレーション、損益集計のテストを追加し、`ModuleNotFoundError` で失敗することを確認した。
- [x] (2026-05-30 19:52 JST) `src/hyperbot/historical_prices.py` と `scripts/fetch_history.py` を実装した。
- [x] (2026-05-30 19:52 JST) `src/hyperbot/grid_backtest.py` と `scripts/run_grid_backtest.py` を実装した。
- [x] (2026-05-30 19:53 JST) README に単独利用方法を追記した。
- [x] (2026-05-30 19:55 JST) `pytest -q`、履歴取得 CLI、バックテスト CLI の検証を実行した。

## Surprises & Discoveries

- Observation: 公式 SDK には `candles_snapshot` があり、`name`、`interval`、`startTime`、`endTime` を渡せばローソク足を取得できる。
  Evidence: ローカルの `hyperliquid.info.Info.candles_snapshot` は `(self, name: str, interval: str, startTime: int, endTime: int) -> Any` というシグネチャである。
- Observation: 初期バックテスト実装では、既存ポジションを売った同じローソク足で同じグリッドを買い戻していた。
  Evidence: `test_backtest_buys_grid_level_and_sells_on_later_candle` が `buy_trade_count == 2` で失敗した。OHLC 順序が不明なため、売却済みレベルは同一足では再エントリーしないように修正した。

## Decision Log

- Decision: 過去価格モジュールは `src/hyperbot/historical_prices.py` とし、`HistoricalPriceClient.fetch_candles(symbol, interval_minutes, lookback, end_time)` を主な入口にする。
  Rationale: Phase 1 の `market_data.py` は現在価格と板の読み取りを担当している。過去価格は単独利用される可能性が高く、CLI からも Bot からも使うため別モジュールにする。
  Date/Author: 2026-05-30 / Codex
- Decision: 分足指定は Hyperliquid が扱う主要な分足だけにマッピングし、未対応の分数は明示的にエラーにする。
  Rationale: API 側が任意分数を受け付けるわけではないため、ユーザーが存在しない間隔を指定したときに暗黙の丸めを行うとバックテスト結果が誤解を招く。
  Date/Author: 2026-05-30 / Codex
- Decision: バックテストは保守的に、新規買いが約定したローソク足では同じ足の中で利確売りを成立させない。
  Rationale: OHLC だけではローソク足内の価格順序が分からない。同じ足で低値と高値の両方を満たす場合に買いと売りを同時成立させると、実際より良い結果を出しやすい。
  Date/Author: 2026-05-30 / Codex
- Decision: 手数料率は `fee_rate` として任意指定にし、デフォルトは `0` にする。
  Rationale: Hyperliquid の手数料はユーザー条件で変わり得る。初期実装では戦略そのものの粗い評価を優先し、必要なら CLI で手数料率を渡せるようにする。
  Date/Author: 2026-05-30 / Codex

## Outcomes & Retrospective

過去価格取得とグリッドバックテストの単独利用機能を実装した。作成した主な成果物は `src/hyperbot/historical_prices.py`、`src/hyperbot/grid_backtest.py`、`scripts/fetch_history.py`、`scripts/run_grid_backtest.py`、`tests/test_historical_prices.py`、`tests/test_grid_backtest.py` である。README には単独実行コマンドと、グリッド本数・間隔の整合条件、OHLC ベースの保守的な約定前提を追記した。

検証では `.\.venv\Scripts\python.exe -m pytest -q` が `20 passed` になった。読み取り専用ライブ確認として、`scripts\fetch_history.py --config config\testnet.yaml --symbol BTC --interval-minutes 60 --lookback 2h --format json` が BTC の 1h ローソク足を 3 件返した。`scripts\run_grid_backtest.py --config config\testnet.yaml --symbol BTC --interval-minutes 60 --lookback 6h --lower-price 65000 --upper-price 75000 --grid-count 5 --grid-spacing 2500 --budget-usd 1000` は 7 本のローソク足でバックテストを行い、`total_pnl=-1.1310344827586206896551724`、`buy_trade_count=1`、`sell_trade_count=0`、`open_position_count=1` の JSON サマリーを返した。

残る制約は、このバックテストが OHLC の近似であり、板、スリッページ、部分約定、資金調達率、実際の注文キュー、価格順序を再現しないことである。これは戦略決定用の粗い検証モジュールであり、注文系の実運用シミュレーションは後続フェーズで扱う。

## Context and Orientation

現在のリポジトリには Phase 1 の読み取り基盤がある。`src/hyperbot/config.py` は Testnet/Mainnet の URL と WebSocket 設定を読み込む。`src/hyperbot/market_data.py` は `allMids` と `l2Book` を取得する。今回追加する過去価格取得は Hyperliquid の `candleSnapshot`、つまり期間を指定してローソク足を取得する Info API を使う。

ローソク足とは、一定時間の始値、高値、安値、終値、出来高を 1 レコードにした価格データである。グリッドバックテストとは、過去のローソク足を順番に見ながら、指定価格に買い注文や売り注文があったと仮定し、現金残高、保有数量、実現損益、未実現損益を計算する検証である。この実装は約定順序が完全には分からない OHLC データに基づくため、精密な取引所シミュレーションではなく戦略検討用の近似である。

## Plan of Work

最初に `tests/test_historical_prices.py` を作り、`interval_minutes` から API の interval 文字列へ変換すること、`lookback` 文字列を時間差へ変換すること、フェイク `Info` の `candles_snapshot` から `Candle` dataclass のタプルへ正規化できることをテストする。次に `tests/test_grid_backtest.py` を作り、グリッド設定から価格レベルを作ること、単純な価格往復で利益が出ること、レンジ外や予算不足で不要な取引をしないことをテストする。

実装では `src/hyperbot/historical_prices.py` に `Candle`、`HistoricalPriceClient`、`interval_to_api_value()`、`parse_lookback()`、`write_candles_csv()` を置く。`HistoricalPriceClient` は `BotConfig` とフェイク可能な `info` を受け取れるようにし、テストはネットワークを使わない。

`src/hyperbot/grid_backtest.py` には `GridBacktestConfig`、`GridBacktestResult`、`GridTrade`、`BacktestPosition`、`run_grid_backtest()` を置く。バックテストは各ローソク足で既存ポジションの売りを先に評価し、その後、新規買いを評価する。新規買いは次のローソク足以降でしか売れないため、同一足の過大評価を避ける。最終損益は、実現損益に加えて、最終終値で残ポジションを評価した未実現損益も別項目として返す。

単独実行用に `scripts/fetch_history.py` と `scripts/run_grid_backtest.py` を作る。前者は `--symbol BTC --interval-minutes 60 --lookback 7d --format csv --output candles.csv` のように使える。後者は同じ価格取得パラメータに加え、`--lower-price`、`--upper-price`、`--grid-count`、`--grid-spacing`、`--budget-usd`、`--fee-rate` を受け取り、JSON でバックテスト結果を表示する。

## Concrete Steps

作業は `C:\Users\Hodaka\Downloads\div\hyperbot` で行う。赤の確認は次で行う。

    .\.venv\Scripts\python.exe -m pytest tests\test_historical_prices.py tests\test_grid_backtest.py -q

実装前は `ModuleNotFoundError` または import エラーで失敗することを期待する。実装後は次を実行し、すべて成功することを期待する。

    .\.venv\Scripts\python.exe -m pytest -q
    git diff --check

読み取り専用のライブ確認は次で行う。

    .\.venv\Scripts\python.exe scripts\fetch_history.py --config config\testnet.yaml --symbol BTC --interval-minutes 60 --lookback 6h --format json

バックテストの手動確認は次で行う。

    .\.venv\Scripts\python.exe scripts\run_grid_backtest.py --config config\testnet.yaml --symbol BTC --interval-minutes 60 --lookback 6h --lower-price 65000 --upper-price 75000 --grid-count 5 --grid-spacing 2500 --budget-usd 1000

## Validation and Acceptance

受け入れ条件は、全テストが通ること、過去価格取得 CLI が指定ティッカー、指定分足、指定期間でローソク足を取得できること、バックテスト CLI が JSON のサマリーを返すことである。バックテスト結果には、総損益、実現損益、未実現損益、ROI、取引数、買い回数、売り回数、未決済ポジション数、最終現金、最終保有数量が含まれる。

## Idempotence and Recovery

テストと読み取り専用 CLI は何度実行しても安全で、秘密鍵や注文権限を使わない。CSV 出力先を指定した場合だけファイルを書き換えるため、必要なら別ファイル名を指定する。ライブ確認がネットワークエラーで失敗した場合は、単体テストが通っていればローカル実装は検証済みとし、エラー内容を記録する。

## Artifacts and Notes

この計画で追加する主なファイルは次の通りである。

    src/hyperbot/historical_prices.py
    src/hyperbot/grid_backtest.py
    scripts/fetch_history.py
    scripts/run_grid_backtest.py
    tests/test_historical_prices.py
    tests/test_grid_backtest.py

## Interfaces and Dependencies

`src/hyperbot/historical_prices.py` は `HistoricalPriceClient.fetch_candles(symbol: str, interval_minutes: int, lookback: timedelta, end_time: datetime | None = None) -> tuple[Candle, ...]` を提供する。`Candle` は `symbol`、`interval`、`open_time_ms`、`close_time_ms`、`open`、`high`、`low`、`close`、`volume`、`trade_count` を持つ。

`src/hyperbot/grid_backtest.py` は `run_grid_backtest(candles: Sequence[Candle], config: GridBacktestConfig) -> GridBacktestResult` を提供する。`GridBacktestConfig` は `lower_price`、`upper_price`、`grid_count`、`grid_spacing`、`budget_usd`、`fee_rate` を持つ。

## Revision Notes

2026-05-30: ユーザー要望に基づき、過去価格取得とグリッドバックテストを単独実行可能なモジュールとして追加する計画を作成した。

2026-05-30: 実装完了に合わせて Progress と Outcomes を更新した。赤確認、単体テスト、Testnet の読み取り専用ライブ確認、バックテスト CLI の結果を追記した。
