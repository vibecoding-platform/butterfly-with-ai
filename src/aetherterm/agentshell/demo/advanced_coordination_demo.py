"""
高度なエージェント間調整のデモンストレーション

親エージェントがエージェント間の複雑な競合を
インテリジェントに解決する例を示します。
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..agents.base import AgentCapability, AgentTask, InterventionType, UserIntervention
from ..service.agent_coordinator import ConflictType, CoordinationStrategy
from ..service.agent_orchestrator import AgentOrchestrator
from ..service.server_connector import ServerConnector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntelligentParentAgent:
    """インテリジェントな親エージェント"""
    
    def __init__(self):
        self.server_connector = ServerConnector()
        self.orchestrator = AgentOrchestrator(self.server_connector)
        
        # 学習データ（過去の決定）
        self.decision_history: List[Dict[str, Any]] = []
        
        # プロジェクトルール
        self.project_rules = {
            "file_ownership": {
                "auth/": "authentication_team",
                "api/": "backend_team",
                "frontend/": "frontend_team"
            },
            "priority_agents": ["critical_fix_agent", "security_agent"],
            "merge_strategies": {
                "models": "additive",  # モデルは追加的にマージ
                "routes": "sequential",  # ルートは順次追加
                "tests": "parallel"  # テストは並列実行可能
            }
        }
        
        # コールバック登録
        self.orchestrator.register_intervention_callback(
            self.intelligent_intervention_handler
        )
        
    async def intelligent_intervention_handler(
        self,
        intervention: UserIntervention
    ) -> Any:
        """インテリジェントな介入処理"""
        logger.info(f"\n[親エージェント] 介入要求を分析中...")
        
        # コンテキストを収集
        context = await self.gather_context(intervention)
        
        # AIによる判断（シミュレート）
        decision = await self.make_intelligent_decision(intervention, context)
        
        # 決定を記録（学習用）
        self.record_decision(intervention, context, decision)
        
        return decision
    
    async def gather_context(
        self,
        intervention: UserIntervention
    ) -> Dict[str, Any]:
        """介入に関するコンテキストを収集"""
        context = {
            "timestamp": datetime.utcnow(),
            "active_agents": len(self.orchestrator._child_agents),
            "intervention_type": intervention.type,
            "message_keywords": self.extract_keywords(intervention.message),
            "conflict_history": self.orchestrator._coordinator.get_conflict_history()
        }
        
        # ファイル関連の情報を抽出
        if "file" in intervention.message.lower():
            context["files"] = self.extract_file_paths(intervention.message)
            context["file_owners"] = self.determine_file_owners(context["files"])
        
        # 過去の類似決定を検索
        context["similar_decisions"] = self.find_similar_decisions(intervention)
        
        return context
    
    async def make_intelligent_decision(
        self,
        intervention: UserIntervention,
        context: Dict[str, Any]
    ) -> str:
        """コンテキストに基づいてインテリジェントな決定を行う"""
        
        # 1. セキュリティチェック
        if self.is_security_risk(intervention, context):
            logger.info("[親エージェント] セキュリティリスクを検出 → 拒否")
            return "キャンセル"
        
        # 2. ファイル所有権チェック
        if "files" in context:
            ownership_decision = self.check_file_ownership(context)
            if ownership_decision:
                logger.info(f"[親エージェント] ファイル所有権に基づく決定: {ownership_decision}")
                return ownership_decision
        
        # 3. 過去の成功パターンを適用
        if context["similar_decisions"]:
            success_pattern = self.analyze_success_patterns(context["similar_decisions"])
            if success_pattern:
                logger.info(f"[親エージェント] 過去の成功パターンを適用: {success_pattern}")
                return success_pattern
        
        # 4. 競合解決戦略
        if context["conflict_history"]:
            conflict_resolution = await self.resolve_conflicts_intelligently(
                intervention, context
            )
            if conflict_resolution:
                return conflict_resolution
        
        # 5. デフォルト判断
        return self.make_default_decision(intervention, context)
    
    def is_security_risk(
        self,
        intervention: UserIntervention,
        context: Dict[str, Any]
    ) -> bool:
        """セキュリティリスクをチェック"""
        risk_keywords = [
            "delete", "drop", "remove", "credentials", "password",
            "secret", "key", "token", "production", "prod"
        ]
        
        message_lower = intervention.message.lower()
        
        # 危険なキーワードの組み合わせをチェック
        if any(kw in message_lower for kw in ["delete", "drop", "remove"]):
            if any(kw in message_lower for kw in ["database", "table", "user", "production"]):
                return True
        
        # 本番環境への直接変更
        if "production" in message_lower and "直接" in intervention.message:
            return True
        
        return False
    
    def check_file_ownership(self, context: Dict[str, Any]) -> Optional[str]:
        """ファイル所有権に基づく決定"""
        files = context.get("files", [])
        owners = context.get("file_owners", [])
        
        # 複数チームのファイルを同時に変更しようとしている場合
        if len(set(owners)) > 1:
            return "修正"  # 分割して実行するよう促す
        
        # 優先エージェントの場合は承認
        for agent_id in self.orchestrator._child_agents:
            if any(priority in agent_id for priority in self.project_rules["priority_agents"]):
                return "承認"
        
        return None
    
    async def resolve_conflicts_intelligently(
        self,
        intervention: UserIntervention,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """競合をインテリジェントに解決"""
        recent_conflicts = context["conflict_history"][-5:]  # 最近の5件
        
        # 同じタイプの競合が繰り返されている場合
        conflict_types = [c.conflict_type for c in recent_conflicts]
        if conflict_types.count(ConflictType.FILE_CONFLICT) >= 3:
            logger.info("[親エージェント] ファイル競合が頻発 → アーキテクチャ見直しを提案")
            return "修正"  # ファイル構造の見直しを促す
        
        # リソース競合が多い場合
        if conflict_types.count(ConflictType.RESOURCE_CONFLICT) >= 2:
            logger.info("[親エージェント] リソース競合が頻発 → 順次実行に切り替え")
            # 調整戦略を変更
            self.orchestrator._coordinator.add_coordination_rule(
                rule_type="force_sequential",
                resource_type="database"
            )
            return "承認"  # 順次実行で承認
        
        return None
    
    def make_default_decision(
        self,
        intervention: UserIntervention,
        context: Dict[str, Any]
    ) -> str:
        """デフォルトの決定ロジック"""
        # 時間帯による判断
        current_hour = datetime.utcnow().hour
        
        # 深夜〜早朝は慎重に
        if 0 <= current_hour < 6:
            if intervention.type == InterventionType.APPROVAL:
                return "修正"  # レビューを促す
        
        # 通常業務時間は積極的に承認
        if 9 <= current_hour < 18:
            if "test" in intervention.message.lower():
                return "承認"  # テストは積極的に実行
        
        # その他はケースバイケース
        if len(self.orchestrator._child_agents) > 3:
            # 多くのエージェントが動いている場合は慎重に
            return "修正"
        
        return "承認"
    
    def extract_keywords(self, message: str) -> List[str]:
        """メッセージからキーワードを抽出"""
        import re
        
        # 単語に分割
        words = re.findall(r'\b\w+\b', message.lower())
        
        # 重要なキーワードをフィルタ
        important_words = [
            w for w in words
            if len(w) > 3 and w not in ['this', 'that', 'with', 'from', 'have']
        ]
        
        return important_words
    
    def extract_file_paths(self, message: str) -> List[str]:
        """メッセージからファイルパスを抽出"""
        import re
        
        # ファイルパスパターン
        patterns = [
            r'[a-zA-Z0-9_/]+\.[a-zA-Z]+',  # path/to/file.ext
            r'`([^`]+)`',  # `で囲まれた部分
        ]
        
        files = []
        for pattern in patterns:
            matches = re.findall(pattern, message)
            files.extend(matches)
        
        return files
    
    def determine_file_owners(self, files: List[str]) -> List[str]:
        """ファイルの所有者を決定"""
        owners = []
        
        for file in files:
            owner = "unknown"
            for path_prefix, team in self.project_rules["file_ownership"].items():
                if file.startswith(path_prefix):
                    owner = team
                    break
            owners.append(owner)
        
        return owners
    
    def find_similar_decisions(
        self,
        intervention: UserIntervention
    ) -> List[Dict[str, Any]]:
        """過去の類似決定を検索"""
        keywords = set(self.extract_keywords(intervention.message))
        
        similar = []
        for decision in self.decision_history[-20:]:  # 最近の20件
            past_keywords = set(decision["keywords"])
            
            # キーワードの重複度を計算
            overlap = len(keywords & past_keywords)
            if overlap >= 2:  # 2つ以上のキーワードが一致
                similar.append(decision)
        
        return similar
    
    def analyze_success_patterns(
        self,
        similar_decisions: List[Dict[str, Any]]
    ) -> Optional[str]:
        """成功パターンを分析"""
        # 成功した決定をカウント
        success_count = {}
        
        for decision in similar_decisions:
            if decision.get("outcome") == "success":
                response = decision["response"]
                success_count[response] = success_count.get(response, 0) + 1
        
        # 最も成功率の高い応答を返す
        if success_count:
            best_response = max(success_count, key=success_count.get)
            if success_count[best_response] >= 2:  # 2回以上成功
                return best_response
        
        return None
    
    def record_decision(
        self,
        intervention: UserIntervention,
        context: Dict[str, Any],
        decision: str
    ) -> None:
        """決定を記録"""
        self.decision_history.append({
            "timestamp": datetime.utcnow(),
            "intervention_type": intervention.type,
            "message": intervention.message,
            "keywords": context.get("message_keywords", []),
            "response": decision,
            "context": context,
            "outcome": None  # 後で更新
        })
        
        # 履歴が大きくなりすぎないように制限
        if len(self.decision_history) > 100:
            self.decision_history = self.decision_history[-50:]


async def demo_intelligent_coordination():
    """インテリジェントな調整のデモ"""
    logger.info("=== インテリジェントエージェント調整デモ ===")
    
    parent = IntelligentParentAgent()
    
    # 複雑なシナリオ: マイクロサービスの同時更新
    agents = [
        {
            "type": "openhands",
            "task_type": "api_update",
            "description": "認証APIのエンドポイント更新",
            "capabilities": [AgentCapability.CODE_EDITING],
            "resources": ["auth/api.py", "auth/models.py", "database"]
        },
        {
            "type": "openhands",
            "task_type": "frontend_update",
            "description": "認証UIの更新",
            "capabilities": [AgentCapability.CODE_EDITING],
            "resources": ["frontend/auth/Login.tsx", "frontend/auth/api.ts"]
        },
        {
            "type": "security_agent",  # 優先エージェント
            "task_type": "security_patch",
            "description": "認証システムのセキュリティパッチ適用",
            "capabilities": [AgentCapability.CODE_EDITING],
            "resources": ["auth/security.py", "auth/models.py"]
        }
    ]
    
    # エージェントを作成
    handles = await parent.orchestrator.create_collaborative_agents(
        agents=agents,
        shared_goal="認証システムの総合アップデート",
        strategy=CoordinationStrategy.COLLABORATIVE
    )
    
    # 各エージェントからの介入要求をシミュレート
    interventions = [
        {
            "agent": list(handles.keys())[0],
            "intervention": UserIntervention(
                type=InterventionType.APPROVAL,
                message="auth/models.pyに新しいUserProfileモデルを追加してよろしいですか？",
                options=["承認", "修正", "キャンセル"]
            )
        },
        {
            "agent": list(handles.keys())[2],  # セキュリティエージェント
            "intervention": UserIntervention(
                type=InterventionType.APPROVAL,
                message="auth/models.pyのUserモデルにセキュリティフィールドを追加する必要があります。緊急度: 高",
                options=["承認", "修正", "キャンセル"]
            )
        },
        {
            "agent": list(handles.keys())[1],
            "intervention": UserIntervention(
                type=InterventionType.CHOICE,
                message="APIの変更に合わせてフロントエンドを更新します。どの方法を選びますか？",
                options=["完全書き換え", "段階的移行", "後方互換性維持"]
            )
        }
    ]
    
    # 介入を処理
    for item in interventions:
        logger.info(f"\n--- エージェント {item['agent']} からの要求 ---")
        response = await parent.orchestrator.handle_intervention_request(
            item["agent"],
            item["intervention"]
        )
        logger.info(f"決定: {response}")
        
        # 決定の結果をシミュレート（成功/失敗）
        if response == "承認":
            # 成功をマーク
            if parent.decision_history:
                parent.decision_history[-1]["outcome"] = "success"
        
        await asyncio.sleep(0.5)  # デモ用の遅延


if __name__ == "__main__":
    asyncio.run(demo_intelligent_coordination())