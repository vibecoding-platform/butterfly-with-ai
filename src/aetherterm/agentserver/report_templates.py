"""
レポートテンプレート

実行レポートと時系列レポートのフォーマッターを提供します。
"""

from datetime import datetime
from typing import List

from ..common.report_models import (
    AgentExecution,
    ExecutionReport,
    TimelineReport,
    WorkSection,
)


class ReportTemplate:
    """レポートテンプレート"""
    
    def generate_execution_report_markdown(self, report: ExecutionReport) -> str:
        """実行詳細レポートをMarkdown形式で生成"""
        return f"""# 実行レポート: {report.title}

## 概要
- **レポートID**: {report.report_id}
- **セッションID**: {report.session_id}
- **作成日時**: {self._format_datetime(report.created_at)}
- **総実行時間**: {self._format_duration(report.total_duration_seconds)}
- **成功率**: {report.success_rate:.1%}

## タスクサマリー
{self._format_task_summary(report.task_summary)}

## 実行統計
- **総ステップ数**: {report.total_steps}
- **失敗ステップ数**: {report.failed_steps}
- **ユーザー介入回数**: {report.total_interventions}

## エージェント実行詳細
{self._format_agent_executions(report.agent_executions)}

## ユーザー介入
{self._format_interventions(report.intervention_details)}

## 成果物
### 生成されたファイル ({len(report.generated_files)})
{self._format_file_list(report.generated_files)}

### 変更されたファイル ({len(report.modified_files)})
{self._format_file_list(report.modified_files)}

## パフォーマンスメトリクス
{self._format_metrics(report.performance_metrics)}

## リソース使用状況
{self._format_metrics(report.resource_metrics)}

## エラーと警告

### エラー ({len(report.errors)})
{self._format_errors(report.errors)}

### 警告 ({len(report.warnings)})
{self._format_warnings(report.warnings)}

---
*レポート生成: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}*
"""
    
    def generate_timeline_report_markdown(self, report: TimelineReport) -> str:
        """時系列作業レポートをMarkdown形式で生成"""
        return f"""# 作業レポート: {report.title}

## 期間
- **開始**: {self._format_datetime(report.period_start)}
- **終了**: {self._format_datetime(report.period_end)}
- **総作業時間**: {self._format_duration(report.total_duration_seconds)}

## サマリー
- **総アクティビティ数**: {report.total_activities}
- **実行コマンド数**: {report.total_commands}
- **作成ファイル数**: {report.files_created}
- **変更ファイル数**: {report.files_modified}

## 主な成果
{self._format_achievements(report.key_achievements)}

## 時系列作業記録

{self._format_timeline_sections(report.work_sections)}

## 発生した問題
{self._format_problems(report.problems_encountered)}

## 次のステップ
{self._format_next_steps(report.next_steps)}

---
*レポート生成: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    def _format_datetime(self, dt: datetime) -> str:
        """日時をフォーマット"""
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    
    def _format_duration(self, seconds: float) -> str:
        """実行時間をフォーマット"""
        if seconds < 60:
            return f"{seconds:.1f}秒"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}分"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}時間"
    
    def _format_task_summary(self, summary: dict) -> str:
        """タスクサマリーをフォーマット"""
        if not summary:
            return "*サマリー情報なし*"
        
        lines = []
        for key, value in summary.items():
            lines.append(f"- **{key}**: {value}")
        
        return "\n".join(lines) if lines else "*サマリー情報なし*"
    
    def _format_agent_executions(self, executions: List[AgentExecution]) -> str:
        """エージェント実行をフォーマット"""
        if not executions:
            return "*エージェント実行なし*"
        
        lines = []
        for i, execution in enumerate(executions, 1):
            lines.append(f"### {i}. {execution.agent_type} ({execution.agent_id})")
            lines.append(f"- **タスクID**: {execution.task_id}")
            lines.append(f"- **開始時刻**: {self._format_datetime(execution.started_at)}")
            
            if execution.completed_at:
                lines.append(f"- **終了時刻**: {self._format_datetime(execution.completed_at)}")
                duration = (execution.completed_at - execution.started_at).total_seconds()
                lines.append(f"- **実行時間**: {self._format_duration(duration)}")
            
            lines.append(f"- **ステータス**: {execution.status}")
            lines.append(f"- **ステップ数**: {len(execution.steps)}")
            lines.append(f"- **介入回数**: {len(execution.interventions)}")
            
            if execution.resource_usage:
                lines.append("- **リソース使用**:")
                for resource, value in execution.resource_usage.items():
                    lines.append(f"  - {resource}: {value}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_interventions(self, interventions: List[dict]) -> str:
        """介入をフォーマット"""
        if not interventions:
            return "*ユーザー介入なし*"
        
        lines = []
        for i, intervention in enumerate(interventions, 1):
            lines.append(f"### {i}. {intervention.get('type', 'unknown')}")
            lines.append(f"- **時刻**: {intervention.get('timestamp', 'unknown')}")
            lines.append(f"- **メッセージ**: {intervention.get('message', '')}")
            lines.append(f"- **応答**: {intervention.get('response', '')}")
            
            response_time = intervention.get('response_time')
            if response_time:
                lines.append(f"- **応答時間**: {response_time:.1f}秒")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_file_list(self, files: List[str]) -> str:
        """ファイルリストをフォーマット"""
        if not files:
            return "*なし*"
        
        lines = []
        for file in sorted(files):
            lines.append(f"- `{file}`")
        
        return "\n".join(lines)
    
    def _format_metrics(self, metrics: dict) -> str:
        """メトリクスをフォーマット"""
        if not metrics:
            return "*メトリクスなし*"
        
        lines = []
        for key, value in sorted(metrics.items()):
            if isinstance(value, float):
                lines.append(f"- **{key}**: {value:.2f}")
            else:
                lines.append(f"- **{key}**: {value}")
        
        return "\n".join(lines)
    
    def _format_errors(self, errors: List[dict]) -> str:
        """エラーをフォーマット"""
        if not errors:
            return "*エラーなし*"
        
        lines = []
        for i, error in enumerate(errors, 1):
            lines.append(f"{i}. **{error.get('type', 'unknown')}**")
            lines.append(f"   - 時刻: {error.get('timestamp', 'unknown')}")
            lines.append(f"   - メッセージ: {error.get('message', '')}")
            
            details = error.get('details')
            if details:
                lines.append(f"   - 詳細: {details}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_warnings(self, warnings: List[dict]) -> str:
        """警告をフォーマット"""
        if not warnings:
            return "*警告なし*"
        
        lines = []
        for i, warning in enumerate(warnings, 1):
            lines.append(f"{i}. **{warning.get('type', 'unknown')}**")
            lines.append(f"   - 時刻: {warning.get('timestamp', 'unknown')}")
            lines.append(f"   - メッセージ: {warning.get('message', '')}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_timeline_sections(self, sections: List[WorkSection]) -> str:
        """時系列セクションをフォーマット"""
        if not sections:
            return "*作業記録なし*"
        
        lines = []
        for i, section in enumerate(sections, 1):
            # セクションヘッダー
            lines.append(f"### {i}. {section.title}")
            
            # 時間情報
            start_time = section.started_at.strftime('%H:%M:%S')
            end_time = section.completed_at.strftime('%H:%M:%S') if section.completed_at else '進行中'
            lines.append(f"*{start_time} - {end_time}*")
            
            # ゴール達成状況
            if section.goal_achieved:
                lines.append("✅ **完了**")
            else:
                lines.append("⚠️ **未完了**")
            
            lines.append("")
            
            # サマリー
            lines.append(section.summary)
            lines.append("")
            
            # アクティビティを時系列で表示
            for activity in section.activities:
                time_str = activity.timestamp.strftime('%H:%M:%S')
                
                # アイコンを決定
                icon_map = {
                    'command': '🔧',
                    'file_create': '📄',
                    'file_edit': '📝',
                    'file_delete': '🗑️',
                    'code_generation': '🤖',
                    'agent_action': '🎯',
                    'user_intervention': '👤',
                    'error': '❌',
                    'warning': '⚠️',
                    'info': 'ℹ️'
                }
                icon = icon_map.get(activity.activity_type.value, '•')
                
                # メインライン
                lines.append(f"{time_str} {icon} **{activity.title}**")
                
                # 詳細情報
                if activity.command:
                    lines.append(f"   ```bash")
                    lines.append(f"   {activity.command}")
                    lines.append(f"   ```")
                    if activity.exit_code is not None:
                        lines.append(f"   Exit code: {activity.exit_code}")
                
                elif activity.file_path:
                    lines.append(f"   File: `{activity.file_path}`")
                    if activity.file_action:
                        lines.append(f"   Action: {activity.file_action}")
                
                elif activity.description:
                    lines.append(f"   {activity.description}")
                
                # 実行時間
                if activity.duration_seconds:
                    lines.append(f"   Duration: {self._format_duration(activity.duration_seconds)}")
                
                lines.append("")
            
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_achievements(self, achievements: List[str]) -> str:
        """成果をフォーマット"""
        if not achievements:
            return "*特記事項なし*"
        
        lines = []
        for achievement in achievements:
            lines.append(f"- ✅ {achievement}")
        
        return "\n".join(lines)
    
    def _format_problems(self, problems: List[str]) -> str:
        """問題をフォーマット"""
        if not problems:
            return "*問題なし*"
        
        lines = []
        for problem in problems:
            lines.append(f"- ⚠️ {problem}")
        
        return "\n".join(lines)
    
    def _format_next_steps(self, next_steps: List[str]) -> str:
        """次のステップをフォーマット"""
        if not next_steps:
            return "*提案なし*"
        
        lines = []
        for i, step in enumerate(next_steps, 1):
            lines.append(f"{i}. {step}")
        
        return "\n".join(lines)