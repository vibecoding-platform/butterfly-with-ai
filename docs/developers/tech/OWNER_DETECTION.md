# セッション所有者判定機能

## 概要

Butterflyターミナルで、閉じたセッションに接続した際に、そのセッションの所有者かどうかを判定し、適切なメッセージを表示する機能です。

## 判定方法

### 1. X-REMOTE-USER ヘッダーによる判定（推奨）

最も信頼性の高い判定方法です。認証プロキシ（nginx、Apache等）が設定したX-REMOTE-USERヘッダーを使用します。

```
X-Remote-User: username
```

- **利点**: 認証済みユーザーの正確な識別が可能
- **適用場面**: 認証プロキシ経由でのアクセス
- **unsecureモード**: 対応可能（プロキシが設定していれば）

### 2. IPアドレスによる判定（フォールバック）

X-REMOTE-USERが利用できない場合のフォールバック方法です。

- **利点**: 設定不要で動作
- **欠点**: NAT環境では複数ユーザーが同じIPを共有する可能性
- **適用場面**: unsecureモードでプロキシ認証がない場合

## 実装詳細

### バックエンド

#### 1. セッション所有者情報の記録

`AsyncioTerminal`クラスでセッション作成時に所有者情報を記録：

```python
# butterfly/terminals/asyncio_terminal.py
class AsyncioTerminal(BaseTerminal):
    session_owners = {}  # {session_id: owner_info}
    
    def __init__(self, ...):
        owner_info = {
            'remote_addr': socket.remote_addr,
            'remote_user': socket.env.get('HTTP_X_REMOTE_USER'),
            'user_name': user.name,
            'created_at': time.time()
        }
        self.session_owners[session] = owner_info
```

#### 2. 所有者判定ロジック

```python
# butterfly/socket_handlers.py
def check_session_ownership(session_id, current_user_info):
    owner_info = AsyncioTerminal.session_owners[session_id]
    
    # X-REMOTE-USER による判定（優先）
    if (current_user_info.get('remote_user') and 
        owner_info.get('remote_user') and
        current_user_info['remote_user'] == owner_info['remote_user']):
        return True
    
    # IPアドレスによる判定（フォールバック）
    if (current_user_info.get('remote_addr') and 
        owner_info.get('remote_addr') and
        current_user_info['remote_addr'] == owner_info['remote_addr']):
        return True
    
    return False
```

### フロントエンド

#### 条件分岐表示

```javascript
function showClosedMessage(data) {
    const isOwnSession = checkIfOwnSession(data);
    
    if (isOwnSession) {
        // 所有者の場合：新しいセッション開始ボタン
        messageDiv.innerHTML = `
            <p>このセッションは終了しました。</p>
            <a href="${newSessionUrl}" class="new-session-link">新しいセッションを開始する</a>
        `;
    } else {
        // 非所有者の場合：URL共有依頼メッセージ
        messageDiv.innerHTML = `
            <p>このセッションは終了しました。</p>
            <p>新しいセッションのURLを共有してもらうよう依頼してください。</p>
        `;
    }
}
```

## 設定例

### nginx プロキシ設定

```nginx
location / {
    proxy_pass http://butterfly-backend;
    proxy_set_header X-Remote-User $remote_user;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header Host $host;
}
```

### Apache プロキシ設定

```apache
ProxyPass / http://butterfly-backend/
ProxyPassReverse / http://butterfly-backend/
ProxyPreserveHost On
ProxyAddHeaders On

# 認証後にX-Remote-Userヘッダーを設定
RequestHeader set X-Remote-User %{REMOTE_USER}e
```

## unsecureモードでの動作

- **X-REMOTE-USERあり**: 正確な所有者判定が可能
- **X-REMOTE-USERなし**: IPアドレスベースの判定（精度は劣る）

## テスト

### 基本テスト
```bash
python test_closed_session.py
```

### 所有者判定テスト
```bash
python test_owner_detection.py
```

## 制限事項

1. **IPアドレス判定の精度**: NAT環境では複数ユーザーが同じIPを共有
2. **セッション情報の永続化**: サーバー再起動で所有者情報が失われる
3. **プロキシ設定依存**: X-REMOTE-USERはプロキシの適切な設定が必要

## セキュリティ考慮事項

- X-REMOTE-USERヘッダーは信頼できるプロキシからのみ受け入れる
- 直接アクセスでのX-REMOTE-USERヘッダー偽装を防ぐ
- セッション所有者情報の適切な管理とクリーンアップ