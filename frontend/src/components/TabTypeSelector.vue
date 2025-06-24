<template>
  <div class="tab-selector-overlay" @click="handleOverlayClick">
    <div class="tab-selector-modal" @click.stop>
      <!-- Modal Header -->
      <div class="modal-header">
        <h2 class="modal-title">新しいタブを作成</h2>
        <button class="close-btn" @click="handleCancel">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2"/>
            <line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2"/>
          </svg>
        </button>
      </div>

      <!-- Tab Type Options -->
      <div class="tab-options">
        <!-- Terminal Tab Option -->
        <div 
          class="tab-option" 
          :class="{ 'selected': selectedType === 'terminal' }"
          @click="selectType('terminal')"
        >
          <div class="option-icon terminal-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="2" y="3" width="20" height="14" rx="2" stroke="currentColor" stroke-width="2"/>
              <path d="m6 8 4 4-4 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="m12 16 4 0" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div class="option-content">
            <h3 class="option-title">ターミナルタブ</h3>
            <p class="option-description">
              標準のターミナルセッション。コマンドライン操作、ファイル管理、開発作業に使用。
            </p>
            <div class="option-features">
              <span class="feature-tag">コマンドライン</span>
              <span class="feature-tag">ファイル操作</span>
              <span class="feature-tag">開発環境</span>
            </div>
          </div>
        </div>

        <!-- AI Agent Tab Option -->
        <div 
          class="tab-option" 
          :class="{ 'selected': selectedType === 'ai_agent' }"
          @click="selectType('ai_agent')"
        >
          <div class="option-icon ai-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
              <path d="9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M12 17h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M8 8l1.5 1.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M16 8l-1.5 1.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div class="option-content">
            <h3 class="option-title">AIエージェントタブ</h3>
            <p class="option-description">
              AI駆動の自動実行環境。タスクの自動化、監視、コラボレーション機能を提供。
            </p>
            <div class="option-features">
              <span class="feature-tag">自動実行</span>
              <span class="feature-tag">タスク管理</span>
              <span class="feature-tag">AI協調</span>
            </div>
          </div>
        </div>
      </div>

      <!-- AI Agent Configuration (shown when AI agent is selected) -->
      <div v-if="selectedType === 'ai_agent'" class="ai-config-section">
        <h3 class="config-title">AIエージェント設定</h3>
        
        <!-- Agent Type Selection -->
        <div class="config-group">
          <label class="config-label">エージェントタイプ</label>
          <select v-model="agentConfig.type" class="config-select">
            <option value="general">汎用エージェント</option>
            <option value="monitoring">監視AI</option>
            <option value="operations">オペレーションAI</option>
            <option value="build">ビルドAI</option>
            <option value="test">テストAI</option>
            <option value="deploy">デプロイAI</option>
          </select>
        </div>

        <!-- Agent Name -->
        <div class="config-group">
          <label class="config-label">エージェント名</label>
          <input 
            v-model="agentConfig.name" 
            type="text" 
            class="config-input"
            placeholder="例: プロジェクト監視エージェント"
          />
        </div>

        <!-- Task Description -->
        <div class="config-group">
          <label class="config-label">実行タスク</label>
          <textarea 
            v-model="agentConfig.task" 
            class="config-textarea"
            placeholder="このエージェントが実行するタスクを説明してください..."
            rows="3"
          ></textarea>
        </div>

        <!-- Autonomy Level -->
        <div class="config-group">
          <label class="config-label">自動化レベル</label>
          <div class="autonomy-options">
            <label class="autonomy-option">
              <input 
                type="radio" 
                v-model="agentConfig.autonomy" 
                value="manual"
              />
              <span class="autonomy-text">
                <strong>手動承認</strong> - すべてのアクションで承認を求める
              </span>
            </label>
            <label class="autonomy-option">
              <input 
                type="radio" 
                v-model="agentConfig.autonomy" 
                value="semi"
              />
              <span class="autonomy-text">
                <strong>半自動</strong> - 重要なアクションのみ承認を求める
              </span>
            </label>
            <label class="autonomy-option">
              <input 
                type="radio" 
                v-model="agentConfig.autonomy" 
                value="auto"
              />
              <span class="autonomy-text">
                <strong>完全自動</strong> - 設定された範囲で自動実行
              </span>
            </label>
          </div>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="modal-actions">
        <button class="btn btn-secondary" @click="handleCancel">
          キャンセル
        </button>
        <button 
          class="btn btn-primary" 
          @click="handleCreate"
          :disabled="!canCreate"
        >
          {{ selectedType === 'terminal' ? 'ターミナルを作成' : 'AIエージェントを作成' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

export interface TabTypeConfig {
  type: 'terminal' | 'ai_agent'
  agentConfig?: {
    type: string
    name: string
    task: string
    autonomy: 'manual' | 'semi' | 'auto'
  }
}

const emit = defineEmits<{
  create: [config: TabTypeConfig]
  cancel: []
}>()

// State
const selectedType = ref<'terminal' | 'ai_agent'>('terminal')
const agentConfig = ref({
  type: 'general',
  name: '',
  task: '',
  autonomy: 'semi' as 'manual' | 'semi' | 'auto'
})

// Computed
const canCreate = computed(() => {
  if (selectedType.value === 'terminal') {
    return true
  }
  
  // For AI agents, require name and task
  return agentConfig.value.name.trim() !== '' && agentConfig.value.task.trim() !== ''
})

// Methods
const selectType = (type: 'terminal' | 'ai_agent') => {
  selectedType.value = type
  
  // Reset agent config when switching types
  if (type === 'ai_agent') {
    agentConfig.value = {
      type: 'general',
      name: '',
      task: '',
      autonomy: 'semi'
    }
  }
}

const handleCreate = () => {
  const config: TabTypeConfig = {
    type: selectedType.value
  }
  
  if (selectedType.value === 'ai_agent') {
    config.agentConfig = { ...agentConfig.value }
  }
  
  emit('create', config)
}

const handleCancel = () => {
  emit('cancel')
}

const handleOverlayClick = () => {
  handleCancel()
}
</script>

<style scoped>
.tab-selector-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  padding: 20px;
  backdrop-filter: blur(4px);
}

.tab-selector-modal {
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  max-width: 700px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  animation: modalSlideIn 0.3s ease-out;
}

@keyframes modalSlideIn {
  from {
    opacity: 0;
    transform: translateY(-20px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 32px;
  border-bottom: 1px solid #e5e7eb;
}

.modal-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1f2937;
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  color: #6b7280;
  cursor: pointer;
  padding: 8px;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: #f3f4f6;
  color: #374151;
}

.tab-options {
  padding: 32px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.tab-option {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 20px;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #ffffff;
}

.tab-option:hover {
  border-color: #d1d5db;
  background: #f9fafb;
}

.tab-option.selected {
  border-color: #3b82f6;
  background: #eff6ff;
}

.option-icon {
  flex-shrink: 0;
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.terminal-icon {
  background: #f0f9ff;
  color: #0369a1;
}

.tab-option.selected .terminal-icon {
  background: #3b82f6;
  color: white;
}

.ai-icon {
  background: #fef3c7;
  color: #d97706;
}

.tab-option.selected .ai-icon {
  background: #f59e0b;
  color: white;
}

.option-content {
  flex: 1;
}

.option-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 8px 0;
}

.option-description {
  color: #6b7280;
  font-size: 0.875rem;
  line-height: 1.5;
  margin: 0 0 12px 0;
}

.option-features {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.feature-tag {
  background: #f3f4f6;
  color: #374151;
  font-size: 0.75rem;
  font-weight: 500;
  padding: 4px 8px;
  border-radius: 6px;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.tab-option.selected .feature-tag {
  background: #dbeafe;
  color: #1e40af;
}

.ai-config-section {
  padding: 0 32px 32px 32px;
  border-top: 1px solid #e5e7eb;
  margin-top: 16px;
  animation: configSlideIn 0.3s ease-out;
}

@keyframes configSlideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.config-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #1f2937;
  margin: 24px 0 20px 0;
}

.config-group {
  margin-bottom: 20px;
}

.config-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: #374151;
  margin-bottom: 6px;
}

.config-select,
.config-input,
.config-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 0.875rem;
  color: #1f2937;
  background: #ffffff;
  transition: border-color 0.2s ease;
}

.config-select:focus,
.config-input:focus,
.config-textarea:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.config-textarea {
  resize: vertical;
  min-height: 80px;
}

.autonomy-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.autonomy-option {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  cursor: pointer;
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.autonomy-option:hover {
  background: #f9fafb;
}

.autonomy-option input[type="radio"] {
  margin-top: 2px;
}

.autonomy-text {
  font-size: 0.875rem;
  line-height: 1.4;
}

.autonomy-text strong {
  color: #1f2937;
  font-weight: 600;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 24px 32px;
  border-top: 1px solid #e5e7eb;
  background: #f9fafb;
  border-radius: 0 0 16px 16px;
}

.btn {
  padding: 10px 20px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.875rem;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 100px;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-secondary {
  background: #e5e7eb;
  color: #374151;
}

.btn-secondary:hover {
  background: #d1d5db;
}

/* Responsive */
@media (max-width: 640px) {
  .tab-selector-modal {
    margin: 20px;
    max-height: calc(100vh - 40px);
  }
  
  .modal-header,
  .tab-options,
  .ai-config-section,
  .modal-actions {
    padding-left: 20px;
    padding-right: 20px;
  }
  
  .tab-options {
    padding-top: 20px;
    padding-bottom: 20px;
  }
  
  .tab-option {
    flex-direction: column;
    text-align: center;
  }
  
  .modal-actions {
    flex-direction: column;
  }
  
  .btn {
    width: 100%;
  }
}
</style>