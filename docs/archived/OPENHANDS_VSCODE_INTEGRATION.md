# OpenHands VSCode統合ガイド

## 概要

OpenHandsをVSCodeから利用するための統合方法と、AetherTermのVSCode拡張機能への統合提案です。

## 現在の利用方法

### 1. ヘッドレスモード

VSCodeの統合ターミナルから実行：

```bash
# 基本的な使用例
docker run -it \
    --pull=always \
    -e SANDBOX_RUNTIME_CONTAINER_IMAGE=docker.all-hands.dev/all-hands-ai/runtime:0.44-nikolaik \
    -e SANDBOX_USER_ID=$(id -u) \
    -e SANDBOX_VOLUMES=$PWD \
    -e LLM_API_KEY=$LLM_API_KEY \
    -e LLM_MODEL="anthropic/claude-3-5-sonnet-20241022" \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v ~/.openhands:/.openhands \
    --add-host host.docker.internal:host-gateway \
    --name openhands-app-$(date +%Y%m%d%H%M%S) \
    docker.all-hands.dev/all-hands-ai/openhands:0.44 \
    python -m openhands.core.main -t "タスクの説明"
```

### 2. CLIモード（インタラクティブ）

```bash
docker run -it \
    --pull=always \
    -e SANDBOX_RUNTIME_CONTAINER_IMAGE=docker.all-hands.dev/all-hands-ai/runtime:0.46-nikolaik \
    -e SANDBOX_USER_ID=$(id -u) \
    -e SANDBOX_VOLUMES=$PWD \
    -e LLM_API_KEY=$LLM_API_KEY \
    -v /var/run/docker.sock:/var/run/docker.sock \
    docker.all-hands.dev/all-hands-ai/openhands:0.46 \
    python -m openhands.cli.main --override-cli-mode true
```

### 3. OpenHands Cloud API

RESTful APIエンドポイント：
- `POST /conversations` - 新しい会話を作成
- `GET /conversations/{id}` - 会話を取得
- `GET /conversations/{id}/files` - ファイルリストを取得
- `GET /vscode-url` - VSCode URLを取得

## AetherTerm VSCode拡張機能への統合提案

### アーキテクチャ

```
VSCode
├── AetherTerm Extension
│   ├── 既存機能
│   │   ├── JupyterHub統合
│   │   ├── ローカル接続
│   │   └── テナント管理
│   └── OpenHands統合（新規）
│       ├── OpenHandsサービス
│       ├── タスクビュー
│       └── コマンドパレット
```

### 実装提案

#### 1. OpenHandsサービスクラス

```typescript
// src/services/openHandsService.ts
import * as vscode from 'vscode';

export interface OpenHandsTask {
    id: string;
    description: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    result?: string;
    createdAt: Date;
}

export class OpenHandsService {
    private apiKey: string | undefined;
    private apiEndpoint = 'https://api.openhands.dev';
    private tasks: Map<string, OpenHandsTask> = new Map();

    constructor(private context: vscode.ExtensionContext) {
        this.loadConfiguration();
    }

    private async loadConfiguration() {
        const config = vscode.workspace.getConfiguration('aetherterm.openhands');
        this.apiKey = await this.context.secrets.get('openhands.apiKey');
        this.apiEndpoint = config.get('apiEndpoint', this.apiEndpoint);
    }

    async executeTask(taskDescription: string, files?: string[]): Promise<string> {
        if (!this.apiKey) {
            const action = await vscode.window.showErrorMessage(
                'OpenHands API key not configured',
                'Configure'
            );
            if (action === 'Configure') {
                await this.configureApiKey();
            }
            throw new Error('API key not configured');
        }

        // タスクを作成
        const task: OpenHandsTask = {
            id: Date.now().toString(),
            description: taskDescription,
            status: 'pending',
            createdAt: new Date()
        };
        this.tasks.set(task.id, task);

        // OpenHands APIを呼び出し
        try {
            const response = await this.callOpenHandsAPI(taskDescription, files);
            task.status = 'completed';
            task.result = response;
            return response;
        } catch (error) {
            task.status = 'failed';
            throw error;
        }
    }

    private async callOpenHandsAPI(task: string, files?: string[]): Promise<string> {
        // 実際のAPI呼び出し実装
        const response = await fetch(`${this.apiEndpoint}/conversations`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.apiKey}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                task: task,
                workspace: vscode.workspace.workspaceFolders?.[0].uri.fsPath,
                files: files
            })
        });

        if (!response.ok) {
            throw new Error(`OpenHands API error: ${response.statusText}`);
        }

        return await response.json();
    }

    async configureApiKey(): Promise<void> {
        const apiKey = await vscode.window.showInputBox({
            prompt: 'Enter your OpenHands API key',
            password: true,
            placeHolder: 'sk-...'
        });

        if (apiKey) {
            await this.context.secrets.store('openhands.apiKey', apiKey);
            this.apiKey = apiKey;
            vscode.window.showInformationMessage('OpenHands API key configured successfully');
        }
    }

    getTasks(): OpenHandsTask[] {
        return Array.from(this.tasks.values());
    }
}
```

#### 2. コマンドの登録

```typescript
// extension.ts に追加
export function activate(context: vscode.ExtensionContext) {
    const openHandsService = new OpenHandsService(context);

    // コマンド: 選択したコードをOpenHandsに送信
    context.subscriptions.push(
        vscode.commands.registerCommand('aetherterm.sendToOpenHands', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                return;
            }

            const selection = editor.selection;
            const selectedText = editor.document.getText(selection);

            if (!selectedText) {
                vscode.window.showWarningMessage('Please select some code first');
                return;
            }

            const task = await vscode.window.showInputBox({
                prompt: 'What would you like OpenHands to do with this code?',
                placeHolder: 'e.g., Add error handling, Optimize performance, Add tests'
            });

            if (task) {
                try {
                    const result = await openHandsService.executeTask(
                        `${task}\n\nCode:\n${selectedText}`
                    );
                    // 結果を新しいエディタに表示
                    const doc = await vscode.workspace.openTextDocument({
                        content: result,
                        language: editor.document.languageId
                    });
                    await vscode.window.showTextDocument(doc);
                } catch (error) {
                    vscode.window.showErrorMessage(`OpenHands error: ${error.message}`);
                }
            }
        })
    );

    // コマンド: ファイル全体をOpenHandsに送信
    context.subscriptions.push(
        vscode.commands.registerCommand('aetherterm.sendFileToOpenHands', async (uri: vscode.Uri) => {
            const task = await vscode.window.showInputBox({
                prompt: 'What would you like OpenHands to do with this file?',
                placeHolder: 'e.g., Add documentation, Refactor, Fix bugs'
            });

            if (task) {
                try {
                    const result = await openHandsService.executeTask(task, [uri.fsPath]);
                    vscode.window.showInformationMessage('OpenHands task completed');
                } catch (error) {
                    vscode.window.showErrorMessage(`OpenHands error: ${error.message}`);
                }
            }
        })
    );

    // タスクビューの追加
    const openHandsProvider = new OpenHandsTaskProvider(openHandsService);
    vscode.window.createTreeView('aethertermOpenHandsTasks', {
        treeDataProvider: openHandsProvider
    });
}
```

#### 3. package.json への追加

```json
{
  "contributes": {
    "commands": [
      {
        "command": "aetherterm.sendToOpenHands",
        "title": "Send to OpenHands",
        "category": "AetherTerm"
      },
      {
        "command": "aetherterm.sendFileToOpenHands",
        "title": "Process File with OpenHands",
        "category": "AetherTerm"
      }
    ],
    "menus": {
      "editor/context": [
        {
          "command": "aetherterm.sendToOpenHands",
          "when": "editorHasSelection",
          "group": "aetherterm@1"
        }
      ],
      "explorer/context": [
        {
          "command": "aetherterm.sendFileToOpenHands",
          "when": "resourceScheme == file",
          "group": "aetherterm@1"
        }
      ]
    },
    "views": {
      "aetherterm": [
        {
          "id": "aethertermOpenHandsTasks",
          "name": "OpenHands Tasks",
          "icon": "$(robot)",
          "contextualTitle": "OpenHands Tasks"
        }
      ]
    },
    "configuration": {
      "title": "AetherTerm OpenHands",
      "properties": {
        "aetherterm.openhands.apiEndpoint": {
          "type": "string",
          "default": "https://api.openhands.dev",
          "description": "OpenHands API endpoint"
        },
        "aetherterm.openhands.model": {
          "type": "string",
          "default": "anthropic/claude-3-5-sonnet-20241022",
          "description": "Default LLM model for OpenHands"
        }
      }
    }
  }
}
```

## 使用例

### 1. コード選択 → OpenHands送信
1. VSCodeでコードを選択
2. 右クリック → "Send to OpenHands"
3. タスクを入力（例: "Add error handling"）
4. OpenHandsが改善されたコードを生成

### 2. ファイル全体の処理
1. エクスプローラーでファイルを右クリック
2. "Process File with OpenHands"
3. タスクを入力（例: "Add comprehensive documentation"）

### 3. コマンドパレット
- `Ctrl+Shift+P` → "AetherTerm: Send to OpenHands"

## 今後の展望

1. **公式VSCode拡張機能のリリース待機**
   - OpenHandsチームが公式拡張機能を開発中の可能性

2. **Continue.devとの統合**
   - Continue.dev拡張機能のバックエンドとしてOpenHandsを使用

3. **AetherTermとの深い統合**
   - AgentShellからOpenHandsを呼び出し
   - ターミナル内でのOpenHandsタスク実行
   - AI協調作業の実現