#!/usr/bin/env python3
"""
実装版のテストスクリプト
"""

import asyncio
import sys
from pathlib import Path

# プロジェクトのパスを追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from demo_cli_langchain_openhands_real import CLILangChainOpenHandsSystem


async def test_system():
    """システムをテスト"""
    print("=== CLI → LangChain → OpenHands 実装版テスト ===\n")
    
    # システム初期化
    system = CLILangChainOpenHandsSystem()
    
    # テストケース
    test_cases = [
        "計算機クラスを作って",
        "Pythonのデコレータについて説明して",
        "フィボナッチ数列を生成する関数を書いて",
        "for i in range(len(list)): print(list[i]) を最適化して"
    ]
    
    for i, test_input in enumerate(test_cases, 1):
        print(f"\n--- テスト {i}/{len(test_cases)} ---")
        print(f"入力: {test_input}")
        
        # 処理実行
        result = await system.process_user_input(test_input)
        
        # 結果表示
        print(f"タスクタイプ: {result['task_type']}")
        print(f"LangChain応答: {result['langchain_response']}")
        print(f"OpenHandsに委譲: {'はい' if result['delegated'] else 'いいえ'}")
        
        if result['delegated']:
            print(f"保存ファイル: {result.get('code_file', 'N/A')}")
            print("生成コード（最初の5行）:")
            lines = result['code_result'].split('\n')[:5]
            for line in lines:
                print(f"  {line}")
            if len(result['code_result'].split('\n')) > 5:
                print("  ...")
        
        print("-" * 60)
        await asyncio.sleep(0.5)
    
    print("\n✅ テスト完了")
    
    # 生成されたファイルを確認
    workspace = Path("/tmp/openhands_workspace")
    if workspace.exists():
        files = list(workspace.glob("*.py"))
        print(f"\n生成されたファイル数: {len(files)}")
        for file in files[-3:]:  # 最新3つ
            print(f"  - {file.name}")


if __name__ == "__main__":
    asyncio.run(test_system())