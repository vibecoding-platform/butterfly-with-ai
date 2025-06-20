"""
Configuration Schema Version Management

プロダクトバージョンとコンフィグスキーマバージョンの対応関係を管理し、
設定ファイルの互換性をチェックします。
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from packaging import version

logger = logging.getLogger(__name__)


@dataclass
class SchemaCompatibility:
    """スキーマ互換性情報"""
    schema_version: str
    product_versions: List[str]
    description: str
    breaking_changes: List[str] = None
    deprecation_warnings: List[str] = None


class ConfigVersionManager:
    """設定スキーマバージョン管理クラス"""
    
    # プロダクトバージョン → スキーマバージョンのマッピング
    SCHEMA_COMPATIBILITY_MAP: Dict[str, SchemaCompatibility] = {
        "1.0.0": SchemaCompatibility(
            schema_version="1.0.0",
            product_versions=["0.1.0", "0.1.1", "0.1.2"],
            description="Initial configuration schema for AetherTerm foundation release",
            breaking_changes=[],
            deprecation_warnings=[]
        ),
        # 将来のバージョン例:
        # "1.1.0": SchemaCompatibility(
        #     schema_version="1.1.0", 
        #     product_versions=["0.2.0", "0.2.1"],
        #     description="Added permission management and multi-tab configuration",
        #     breaking_changes=["auth.permission_level structure changed"],
        #     deprecation_warnings=["features.old_setting deprecated in favor of features.new_setting"]
        # ),
    }
    
    # 現在のプロダクトバージョン（通常は__version__から取得）
    CURRENT_PRODUCT_VERSION = "0.1.0"
    
    def __init__(self):
        """バージョンマネージャーを初期化"""
        self._validate_compatibility_map()
        
    def _validate_compatibility_map(self):
        """互換性マップの整合性をチェック"""
        schema_versions = set()
        for schema_version, compat in self.SCHEMA_COMPATIBILITY_MAP.items():
            if schema_version != compat.schema_version:
                raise ValueError(f"Schema version mismatch: key={schema_version}, value={compat.schema_version}")
            schema_versions.add(schema_version)
            
        logger.debug(f"Validated {len(schema_versions)} schema versions")
        
    def get_current_schema_version(self) -> str:
        """現在のプロダクトバージョンに対応するスキーマバージョンを取得"""
        for compat in self.SCHEMA_COMPATIBILITY_MAP.values():
            if self.CURRENT_PRODUCT_VERSION in compat.product_versions:
                return compat.schema_version
                
        # フォールバック: 最新のスキーマバージョン
        latest_schema = max(self.SCHEMA_COMPATIBILITY_MAP.keys(), key=version.parse)
        logger.warning(f"No schema found for product version {self.CURRENT_PRODUCT_VERSION}, using latest: {latest_schema}")
        return latest_schema
        
    def is_schema_compatible(self, config_schema_version: str) -> Tuple[bool, List[str]]:
        """
        設定ファイルのスキーマバージョンが現在のプロダクトと互換性があるかチェック
        
        Returns:
            Tuple[bool, List[str]]: (互換性あり, 警告メッセージリスト)
        """
        warnings = []
        
        # スキーマバージョンが存在するかチェック
        if config_schema_version not in self.SCHEMA_COMPATIBILITY_MAP:
            return False, [f"Unknown schema version: {config_schema_version}"]
            
        compat = self.SCHEMA_COMPATIBILITY_MAP[config_schema_version]
        
        # 現在のプロダクトバージョンが対応リストにあるかチェック
        if self.CURRENT_PRODUCT_VERSION not in compat.product_versions:
            # バージョン範囲での互換性チェック
            is_compatible, version_warnings = self._check_version_range_compatibility(
                config_schema_version, self.CURRENT_PRODUCT_VERSION
            )
            warnings.extend(version_warnings)
            
            if not is_compatible:
                return False, warnings
                
        # 非推奨警告をチェック
        if compat.deprecation_warnings:
            warnings.extend([f"Deprecation: {warning}" for warning in compat.deprecation_warnings])
            
        return True, warnings
        
    def _check_version_range_compatibility(self, config_schema_version: str, product_version: str) -> Tuple[bool, List[str]]:
        """バージョン範囲での互換性をチェック"""
        warnings = []
        
        try:
            config_ver = version.parse(config_schema_version)
            product_ver = version.parse(product_version)
            
            # 基本的な互換性ルール:
            # - メジャーバージョンが同じなら互換性あり（警告付き）
            # - メジャーバージョンが異なる場合は非互換
            if config_ver.major == product_ver.major:
                if config_ver != product_ver:
                    warnings.append(f"Schema version {config_schema_version} may not be fully compatible with product version {product_version}")
                return True, warnings
            else:
                return False, [f"Schema version {config_schema_version} is incompatible with product version {product_version} (major version mismatch)"]
                
        except Exception as e:
            logger.error(f"Version parsing error: {e}")
            return False, [f"Invalid version format: {e}"]
            
    def get_schema_info(self, schema_version: str) -> Optional[SchemaCompatibility]:
        """スキーマバージョンの詳細情報を取得"""
        return self.SCHEMA_COMPATIBILITY_MAP.get(schema_version)
        
    def get_supported_schemas(self) -> List[str]:
        """サポートされているスキーマバージョンのリストを取得"""
        return list(self.SCHEMA_COMPATIBILITY_MAP.keys())
        
    def get_recommended_schema_version(self) -> str:
        """推奨スキーマバージョンを取得（現在のプロダクトバージョンに最適）"""
        return self.get_current_schema_version()
        
    def validate_config_schema_version(self, config_data: Dict) -> Tuple[bool, str, List[str]]:
        """
        設定データからスキーマバージョンを検証
        
        Returns:
            Tuple[bool, str, List[str]]: (有効, スキーマバージョン, 警告リスト)
        """
        # スキーマバージョンの存在チェック
        if "schema_version" not in config_data:
            recommended = self.get_recommended_schema_version()
            return False, "", [f"Missing schema_version in configuration. Recommended: {recommended}"]
            
        config_schema_version = config_data["schema_version"]
        
        # スキーマバージョンの型チェック
        if not isinstance(config_schema_version, str):
            return False, str(config_schema_version), ["schema_version must be a string"]
            
        # 互換性チェック
        is_compatible, warnings = self.is_schema_compatible(config_schema_version)
        
        return is_compatible, config_schema_version, warnings
        
    def suggest_upgrade_path(self, current_schema: str) -> Optional[str]:
        """
        現在のスキーマから推奨スキーマへのアップグレードパスを提案
        （将来のマイグレーション機能で使用予定）
        """
        current_ver = version.parse(current_schema) if current_schema else version.parse("0.0.0")
        recommended_ver = version.parse(self.get_recommended_schema_version())
        
        if current_ver < recommended_ver:
            return f"Consider upgrading from schema {current_schema} to {self.get_recommended_schema_version()}"
        elif current_ver > recommended_ver:
            return f"Schema {current_schema} is newer than recommended {self.get_recommended_schema_version()}"
        else:
            return None
            
    def get_version_summary(self) -> Dict:
        """バージョン情報のサマリーを取得"""
        return {
            "current_product_version": self.CURRENT_PRODUCT_VERSION,
            "current_schema_version": self.get_current_schema_version(),
            "supported_schemas": self.get_supported_schemas(),
            "total_schemas": len(self.SCHEMA_COMPATIBILITY_MAP),
        }


# グローバルバージョンマネージャー
_version_manager: Optional[ConfigVersionManager] = None


def get_version_manager() -> ConfigVersionManager:
    """グローバルバージョンマネージャーを取得"""
    global _version_manager
    if _version_manager is None:
        _version_manager = ConfigVersionManager()
    return _version_manager


def validate_schema_version(config_data: Dict) -> Tuple[bool, str, List[str]]:
    """設定データのスキーマバージョンを検証（便利関数）"""
    return get_version_manager().validate_config_schema_version(config_data)