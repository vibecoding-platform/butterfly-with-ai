# AI連携とチャット機能の実装計画

本プロジェクトは、Webベースのターミナルを提供するアプリです。
本プロジェクトを改造して、入出力をAIに行うことにより、解析と、ユーザーに対する提案を行いたいです。

そのために、入出力をAIを行う仕組みをまずは実装します。
また、AIからの解析結果をユーザーに提示する為のチャットを組み込みます。
また、チャットからは、ターミナル部分にコマンドをコピーするといった挙動が挙げられます。

## 計画の概要

1.  **AI連携モジュールの作成:** ターミナルの入出力をAIに送信し、AIからの応答を受け取るための新しいPythonモジュールを作成します。
2.  **ターミナル入出力のAIへのルーティング:** ユーザー入力をAI連携モジュールに送信し、AIからの応答をターミナルに書き込むように変更します。また、ターミナルからの出力もAI連携モジュールに送信し、解析させます。
3.  **チャット機能の実装:** 新しいWebソケットハンドラを作成し、AIとのチャットインターフェースを提供します。チャットからターミナルへのコマンドコピー機能も実装します。
4.  **フロントエンドの変更:** チャットUIを追加し、新しいチャットWebソケットとの通信、AIからの提案の表示、およびチャットからのコマンドコピー機能を実装します。
5.  **Dependency-Injectorの導入:** 既存のコードを壊さないように、依存性注入（Dependency Injection）ライブラリである `dependency-injector` を導入し、各コンポーネントの結合度を低減させます。

## 具体的な計画ステップ

1.  **AI連携モジュールの作成 (`butterfly/ai_integration.py`):**
    *   AIモデルとのインターフェースを定義するクラスを作成します。
    *   `process_terminal_input(user_input)`: ユーザー入力をAIに渡し、AIが生成したコマンドや解析結果を返すメソッド。
    *   `process_terminal_output(terminal_output)`: ターミナル出力をAIに渡し、解析結果や提案を返すメソッド。
    *   `process_chat_message(chat_message)`: チャットメッセージをAIに渡し、AIの応答を返すメソッド。

2.  **`butterfly/routes.py` の変更:**
    *   `TermWebSocket` クラスを修正し、`on_message` メソッドでAI連携モジュールを呼び出すようにします。
    *   `Terminal` クラスの出力ブロードキャスト部分を修正し、AI連携モジュールにターミナル出力を送信するようにします。
    *   新しい `ChatWebSocket` クラスを追加し、チャットメッセージの送受信を処理します。

3.  **`butterfly/terminal.py` の変更:**
    *   ターミナル出力がブロードキャストされる際に、AI連携モジュールにその出力を渡すためのフックを追加します。

4.  **`butterfly/templates/index.html` の変更:**
    *   チャットUI（テキストエリア、送信ボタン、メッセージ表示領域など）を追加します。

5.  **フロントエンドJavaScript/CoffeeScriptの変更:**
    *   `coffees/main.coffee` または `coffees/term.coffee` に、新しい `ChatWebSocket` との接続ロジックを追加します。
    *   チャットメッセージの送信、AI応答の表示、およびチャットからのコマンドコピー機能を実装します。

6.  **`dependency-injector` の導入:**
    *   `requirements.txt` に `dependency-injector` を追加します。
    *   アプリケーションのエントリポイント（例: `butterfly.server.py` や `butterfly/__init__.py`）でコンテナをセットアップします。
    *   `TermWebSocket` や `ChatWebSocket`、`AIIntegrationModule` などのクラスが依存するオブジェクトをコンテナ経由で注入するようにリファクタリングします。これにより、テスト容易性と保守性を向上させます。

## Mermaid Diagram

```mermaid
graph TD
    A[User] -->|Input| B(Web Browser)
    B -->|WebSocket /ws (Terminal Input)| C(TermWebSocket)
    C -->|Process Input| D(AI Integration Module)
    D -->|AI Generated Command| E(Terminal)
    E -->|Terminal Output| D
    D -->|AI Analysis/Suggestion| F(ChatWebSocket)
    F -->|Chat Message| B
    B -->|WebSocket /ctl (Command Copy)| G(TermCtlWebSocket)
    G -->-->|Control Command| E
    E -->|Terminal Output| C
    C -->|WebSocket /ws (Terminal Output)| B