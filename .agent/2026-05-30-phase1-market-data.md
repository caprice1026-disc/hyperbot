# Phase 1 読み取り系マーケットデータ実装

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

この計画はリポジトリ直下の `PLANS.md` に従って維持する。作業ディレクトリは `C:\Users\Hodaka\Downloads\div\hyperbot` とする。

## Purpose / Big Picture

この変更で、Bot は注文を出さずに Hyperliquid Testnet から読み取り専用の市場データを取得できるようになる。利用者は設定ファイルを選んで、現在価格一覧である `allMids`、指定銘柄の板情報である `l2Book`、WebSocket のリアルタイム購読を確認できる。Phase 1 では秘密鍵、実注文、キャンセル、ポジション操作は扱わないため、後続フェーズの前に安全な読み取り基盤だけを検証できる。

## Progress

- [x] (2026-05-30 18:45 JST) 貼り付けテキストを UTF-8 として読み直し、Phase 1 が「設定ファイル作成、Hyperliquid SDK 導入、Testnet 接続、allMids 取得、l2Book 取得、WebSocket 接続、WebSocket 再接続処理」であることを確認した。
- [x] (2026-05-30 18:49 JST) 公式 SDK `hyperliquid-python-sdk==0.23.0`、`PyYAML`、`pytest` がローカル仮想環境に入ることを確認した。
- [x] (2026-05-30 18:55 JST) TDD で設定読み込み、REST 変換、WebSocket 再接続のテストを先に追加し、`ModuleNotFoundError: No module named 'hyperbot'` で失敗することを確認した。
- [x] (2026-05-30 19:04 JST) `src/hyperbot` に Phase 1 の最小実装を追加した。
- [x] (2026-05-30 19:04 JST) README と実行スクリプトを更新し、手元で検証できる入口を作った。
- [x] (2026-05-30 19:07 JST) `pytest -q`、editable install、REST Testnet 読み取り、WebSocket 1 メッセージ受信を実行して成功を確認した。
- [x] (2026-05-30 19:12 JST) 自己レビューで WebSocket クライアントが `BaseException` を捕まえていた点を `Exception` に修正し、再検証した。

## Surprises & Discoveries

- Observation: 公式 SDK の `Info.__init__` は `skip_ws=True` でもメタデータ取得のため REST を呼ぶ。そのため単体テストでは SDK 実体を直接作らず、`Info` 互換のフェイクを注入する必要がある。
  Evidence: ローカルにインストールした `hyperliquid.info.Info` のシグネチャは `Info(base_url=None, skip_ws=False, meta=None, spot_meta=None, perp_dexs=None, timeout=None)` で、`all_mids()` と `l2_snapshot(name)` が存在する。
- Observation: 公式 SDK の `WebsocketManager` は購読管理を持つが、明示的な再接続ループを公開していない。Phase 1 の「WebSocket 再接続処理」は SDK REST ラッパーとは別に、公式 WebSocket プロトコルへ再接続する小さなクライアントで実装する。
  Evidence: ローカルの `hyperliquid/websocket_manager.py` は `run_forever()` を一度呼ぶスレッド構造で、終了後に購読を再作成する外側のループを持たない。

## Decision Log

- Decision: Python パッケージは `src/hyperbot` に置き、CLI 用の薄いスクリプトを `scripts` に置く。
  Rationale: ルートがほぼ空であるため、`src` レイアウトにするとテストと実行スクリプトから同じパッケージを import できる。貼り付けテキストの `src/market_data.py` という責務分割は、`src/hyperbot/market_data.py` として反映する。
  Date/Author: 2026-05-30 / Codex
- Decision: REST の `allMids` と `l2Book` は公式 SDK `hyperliquid.info.Info` を使い、戻り値は `Decimal` と dataclass に正規化する。
  Rationale: 後続の戦略計算で浮動小数点誤差を避けるため、価格と数量は `Decimal` として扱う。SDK の生レスポンスは文字列価格を含むため、境界で正規化する。
  Date/Author: 2026-05-30 / Codex
- Decision: WebSocket は `websocket-client` で公式購読メッセージを送る再接続クライアントとして実装する。
  Rationale: Phase 1 では接続、購読、再接続を明示的にテストしたい。公式 SDK は内部スレッドで WebSocket を開始するため、再接続の赤緑テストが書きにくい。SDK は REST 読み取りに使い、WebSocket プロトコルは公式形式 `{method: subscribe, subscription: ...}` に限定する。
  Date/Author: 2026-05-30 / Codex

## Outcomes & Retrospective

Phase 1 の読み取り系は完了した。作成した主な成果物は、設定ファイル `config/testnet.yaml` と `config/mainnet.yaml`、設定読み込み `src/hyperbot/config.py`、REST 読み取り `src/hyperbot/market_data.py`、WebSocket 購読と再接続 `src/hyperbot/ws.py`、実行入口 `scripts/run_testnet.py` と `scripts/watch_testnet_ws.py`、単体テスト 9 件である。

検証では `.\.venv\Scripts\python.exe -m pytest -q` が `9 passed` になった。`scripts\run_testnet.py --config config\testnet.yaml --symbol BTC` は Testnet から `mid=71716.0`、`best_bid=71669.0`、`best_ask=71763.0` を取得した。`scripts\watch_testnet_ws.py --config config\testnet.yaml --subscription allMids --max-messages 1` は `allMids` の WebSocket メッセージを 1 件受信した。残る制約は、WebSocket の手動スクリプトが生 JSON をそのまま出力するため `allMids` では出力が大きいこと、注文系とリスク管理はまだ実装していないことである。

最終確認として、例外処理修正後に `pytest -q` が再度 `9 passed` になった。さらに `scripts\run_testnet.py --config config\testnet.yaml --symbol BTC` は `mid=71716.0`、`best_bid=71669.0`、`best_ask=71763.0` を返し、`scripts\watch_testnet_ws.py --config config\testnet.yaml --subscription l2Book --symbol BTC --max-messages 1` は BTC の `l2Book` WebSocket メッセージを 1 件受信した。

## Context and Orientation

現在のリポジトリは `README.md`、`PLANS.md`、`AGENTS.md` だけを持つ、ほぼ空の Python プロジェクトである。仮想環境は `.venv` にあり、Python は 3.13.1 である。Phase 1 の対象は読み取り専用の市場データであり、注文系、ウォレット秘密鍵、DB、リスク管理、グリッド戦略は後続フェーズに残す。

`allMids` は Hyperliquid の Info API が返す全銘柄の中間価格一覧である。`l2Book` は売り板と買い板のスナップショットで、価格 `px`、数量 `sz`、同価格の注文数 `n` を含む。WebSocket は HTTP のような単発取得ではなく、接続を開いたままサーバーから更新を受け取る仕組みである。再接続処理とは、接続が切れたり `run_forever` が例外で終わった場合に、購読内容を保持したまま新しい接続を作り直す処理を指す。

## Plan of Work

まず `pyproject.toml` と `requirements.txt` を作成し、`hyperliquid-python-sdk==0.23.0`、`PyYAML`、`websocket-client`、テスト用の `pytest` を明示する。次に `config/testnet.yaml` と `config/mainnet.yaml` を追加し、REST URL、WebSocket URL、既定銘柄、タイムアウト、再接続回数を設定として表現する。

TDD の最初の赤として、`tests/test_config.py` に設定ファイルを読み込むテストを書く。次に `tests/test_market_data.py` にフェイク `Info` を使った `all_mids`、`mid_price`、`l2_book` の正規化テストを書く。最後に `tests/test_websocket.py` で、WebSocket クライアントが購読メッセージを送ること、メッセージを callback に流すこと、失敗後に再接続して再購読することを検証する。これらを実装前に実行し、`ModuleNotFoundError` または未実装エラーで失敗することを確認する。

実装では `src/hyperbot/config.py` に dataclass と `load_config()` を置く。`src/hyperbot/market_data.py` には `HyperliquidMarketData`、`BookLevel`、`OrderBookSnapshot` を置き、`Info` の生成はコンストラクタ引数で差し替え可能にする。`src/hyperbot/ws.py` には `HyperliquidWebSocketClient` と購読ヘルパーを置き、`websocket.WebSocketApp` の生成関数をテストで差し替えられるようにする。

最後に `scripts/run_testnet.py` で Testnet の `allMids` と `l2Book` を一度取得する読み取り専用スクリプトを作る。`scripts/watch_testnet_ws.py` は WebSocket の `allMids` を短時間表示する入口にする。README にはインストール、テスト、読み取り確認のコマンドを追記する。

## Concrete Steps

作業は `C:\Users\Hodaka\Downloads\div\hyperbot` で行う。依存関係の導入は次のコマンドで再現できる。

    .\.venv\Scripts\python.exe -m pip install -e .[dev]

赤の確認では次を実行する。

    .\.venv\Scripts\python.exe -m pytest -q

実装前は import 失敗や未定義のため失敗することが期待値である。実装後はすべてのテストが通ることを期待する。

読み取り専用のライブ確認は次で行う。

    .\.venv\Scripts\python.exe scripts\run_testnet.py --config config\testnet.yaml --symbol BTC

成功時は BTC の mid price と l2Book の best bid / best ask が表示される。これは注文を出さない。

WebSocket の手動確認は次で行う。

    .\.venv\Scripts\python.exe scripts\watch_testnet_ws.py --config config\testnet.yaml --subscription allMids --max-messages 1

成功時は `allMids` の WebSocket メッセージを 1 件表示して終了する。

## Validation and Acceptance

受け入れ条件は、`pytest -q` が成功し、設定読み込み、REST 正規化、WebSocket 再接続の単体テストがすべて通ることである。さらにネットワークが利用可能な場合、`scripts/run_testnet.py` が Testnet から BTC の価格と板を読み取れることを確認する。WebSocket は `scripts/watch_testnet_ws.py` で少なくとも 1 件のメッセージを受け取れることを確認する。

テストは外部ネットワークに依存しない。ライブ確認は Hyperliquid Testnet の状態とネットワークに依存するため、失敗しても単体テストが通っていればローカル実装の検証は完了と見なせる。ただし、その場合は失敗理由を記録する。

## Idempotence and Recovery

`pip install -e .[dev]` と `pytest -q` は何度実行しても安全である。WebSocket 手動確認は読み取り専用で、秘密鍵も注文権限も使わない。ライブ確認が接続エラーで失敗した場合は、しばらく待って同じコマンドを再実行する。作成する設定ファイルには秘密情報を置かない。

## Artifacts and Notes

この計画で作る主なファイルは次の通りである。

    pyproject.toml
    requirements.txt
    config/testnet.yaml
    config/mainnet.yaml
    src/hyperbot/__init__.py
    src/hyperbot/config.py
    src/hyperbot/market_data.py
    src/hyperbot/ws.py
    scripts/run_testnet.py
    scripts/watch_testnet_ws.py
    tests/test_config.py
    tests/test_market_data.py
    tests/test_websocket.py

## Interfaces and Dependencies

`src/hyperbot/config.py` は `load_config(path: str | Path) -> BotConfig` を提供する。`BotConfig` は `environment`、`symbol`、`network`、`request_timeout_seconds`、`websocket` を持つ。

`src/hyperbot/market_data.py` は `HyperliquidMarketData(config: BotConfig, info: Any | None = None)` を提供する。`all_mids()` は `dict[str, Decimal]` を返す。`mid_price(symbol: str)` は指定銘柄の `Decimal` を返し、存在しない場合は `MarketDataError` を送出する。`l2_book(symbol: str)` は `OrderBookSnapshot` を返す。

`src/hyperbot/ws.py` は `HyperliquidWebSocketClient(config: BotConfig, websocket_app_factory: Callable | None = None)` を提供する。`subscribe_all_mids(callback)` と `subscribe_l2_book(symbol, callback)` で購読を登録し、`run_forever(max_reconnects: int | None = None)` で接続を開始する。接続が失敗または終了した場合、`stop()` が呼ばれていなければ設定に従って再接続する。

## Revision Notes

2026-05-30: Phase 1 実装開始時点の計画を作成した。リポジトリがほぼ空だったため、設定、REST、WebSocket、スクリプト、テストを一括で立ち上げる方針を明文化した。

2026-05-30: Phase 1 実装完了に合わせて Progress と Outcomes を更新した。テストと読み取り専用ライブ確認の実行結果を、将来の再開者が同じ検証を再現できるように記録した。

2026-05-30: 自己レビューで見つけた WebSocket 例外処理の過剰捕捉を修正した。通常の接続例外は再接続対象にしつつ、`KeyboardInterrupt` や `SystemExit` は握りつぶさないためである。
