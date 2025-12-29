<template>
  <div class="ai-governance-container">
    <div class="header-section">
      <h2>
        <el-icon><Setting /></el-icon>
        AI 进化控制台
      </h2>
      <p class="subtitle">
        监控系统自进化状态，管理 Prompt 版本与多智能体共识。
      </p>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="label">Prompt 版本迭代</div>
        <div class="value">
          {{ totalVersions }} <span class="unit">次</span>
        </div>
        <div class="desc">最近更新: {{ lastUpdateTime }}</div>
      </div>
      <div class="stat-card warning">
        <div class="label">待分析误判</div>
        <div class="value">
          {{ pendingCorrections }} <span class="unit">例</span>
        </div>
        <div class="action">
          <el-button 
            type="primary" 
            size="small"
            @click="triggerAnalysis" 
            :disabled="analyzing"
            :loading="analyzing"
          >
            <el-icon v-if="!analyzing"><MagicStick /></el-icon>
            {{ analyzing ? "分析中..." : "触发元分析" }}
          </el-button>
        </div>
      </div>
      <div class="stat-card">
        <div class="label">人工修正记录</div>
        <div class="value">
          {{ totalCorrections }} <span class="unit">条</span>
        </div>
        <div class="action">
          <el-button type="success" size="small" @click="openCorrectionDialog">
            <el-icon><Edit /></el-icon> 手动修正
          </el-button>
        </div>
      </div>
    </div>

    <div class="main-content">
      <div class="panel evolution-panel">
        <div class="panel-header">
          <h3>🧬 Prompt 进化基因</h3>
          <select v-model="selectedPromptType" @change="fetchVersions">
            <option value="COMMENT">评论区审核 (Comment)</option>
            <option value="DANMAKU">弹幕审核 (Danmaku)</option>
          </select>
        </div>

        <div class="timeline">
          <div
            v-for="version in versions"
            :key="version.id"
            class="timeline-item"
            :class="{ active: selectedVersion?.id === version.id }"
            @click="selectedVersion = version"
          >
            <div class="time">{{ formatDate(version.created_at) }}</div>
            <div class="reason">{{ version.update_reason }}</div>
            <div class="meta">Operator ID: {{ version.updated_by }}</div>
          </div>
        </div>
      </div>

      <div class="panel detail-panel">
        <div v-if="selectedVersion && !analysisResult" class="version-detail">
          <div class="detail-header">
            <h3>版本 V{{ selectedVersion.id }} 详情</h3>
            <div class="actions">
               <el-switch
                v-model="showDiff"
                active-text="Diff 对比"
                inactive-text="源码模式"
              />
              <span class="tag">{{ selectedVersion.prompt_type }}</span>
            </div>
          </div>

          <!-- Diff View / Code View -->
          <div class="code-preview" v-if="!showDiff">
            <pre>{{ selectedVersion.prompt_content }}</pre>
          </div>
          <div class="diff-view" v-else>
            <div class="diff-column">
              <div class="diff-header">上一版本 (V{{ getPreviousVersion(selectedVersion)?.id || 'Null' }})</div>
              <pre>{{ getPreviousVersion(selectedVersion)?.prompt_content || '// 无上一版本' }}</pre>
            </div>
            <div class="diff-column current">
              <div class="diff-header">当前版本 (V{{ selectedVersion.id }})</div>
              <pre>{{ selectedVersion.prompt_content }}</pre>
            </div>
          </div>
        </div>

        <div v-if="analysisResult" class="analysis-result">
          <div class="result-header">
            <h3>
              <el-icon><Search /></el-icon>
              错误模式元分析报告
            </h3>
            <el-button 
              type="info" 
              size="small"
              @click="analysisResult = null"
            >
              关闭
            </el-button>
          </div>

          <div class="analysis-content">
            <div
              class="markdown-body"
              v-html="renderMarkdown(analysisResult.suggestions)"
            ></div>
          </div>

          <div class="apply-actions">
            <textarea
              v-model="newPromptDraft"
              placeholder="在此微调 AI 建议的 Prompt..."
              class="prompt-editor"
            ></textarea>
            <div class="btn-group">
              <el-button @click="analysisResult = null">
                放弃
              </el-button>
              <el-button type="primary" @click="applyOptimization">
                🚀 应用此进化
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Manual Correction Dialog -->
    <el-dialog v-model="correctionDialogVisible" title="提交人工修正 (Misjudgment Feedback)" width="500px">
      <el-form :model="correctionForm" label-width="100px">
        <el-form-item label="内容类型">
          <el-radio-group v-model="correctionForm.type">
            <el-radio label="COMMENT">评论</el-radio>
            <el-radio label="DANMAKU">弹幕</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="原始内容">
          <el-input v-model="correctionForm.content" type="textarea" :rows="3" placeholder="输入被误判的内容..." />
        </el-form-item>
        <el-form-item label="原始评分">
          <el-input-number v-model="correctionForm.originalScore" :min="0" :max="100" />
        </el-form-item>
        <el-form-item label="正评分">
          <el-input-number v-model="correctionForm.correctedScore" :min="0" :max="100" />
        </el-form-item>
        <el-form-item label="修正原因">
          <el-input v-model="correctionForm.reason" placeholder="例如：这是流行梗，非违规" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="correctionDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitCorrection">提交修正</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { Edit, Search, Setting, MagicStick } from "@element-plus/icons-vue";
import {
  adminAiApi,
  type PromptVersion,
  type ErrorPatternAnalysis,
} from "../api/admin.api";
import { formatDate } from "@/shared/utils/formatters";
import { ElMessage } from "element-plus";

// 状态
const versions = ref<PromptVersion[]>([]);
const totalVersions = ref(0);
const lastUpdateTime = ref("-");
const selectedPromptType = ref("COMMENT");
const selectedVersion = ref<PromptVersion | null>(null);
const showDiff = ref(false);

const pendingCorrections = ref(12);
const totalCorrections = ref(0); // 实际应从 API 获取
const analyzing = ref(false);
const analysisResult = ref<ErrorPatternAnalysis | null>(null);
const newPromptDraft = ref("");

// Correction Dialog
const correctionDialogVisible = ref(false);
const correctionForm = ref({
  type: "COMMENT",
  content: "",
  originalScore: 0,
  correctedScore: 100,
  reason: ""
});

// 方法
const fetchVersions = async () => {
  try {
    const res = await adminAiApi.getPromptVersions({
      prompt_type: selectedPromptType.value,
      limit: 20,
    });

    if (res.success) {
      versions.value = res.data.items;
      totalVersions.value = res.data.total;

      if (versions.value.length > 0) {
        selectedVersion.value = versions.value[0];
        lastUpdateTime.value = formatDate(versions.value[0].created_at);
      }
    }
  } catch (e) {
    console.error("加载版本失败", e);
  }
};

const getPreviousVersion = (current: PromptVersion) => {
  const index = versions.value.findIndex(v => v.id === current.id);
  if (index !== -1 && index + 1 < versions.value.length) {
    return versions.value[index + 1];
  }
  return null;
};

const triggerAnalysis = async () => {
  analyzing.value = true;
  try {
    const res = await adminAiApi.analyzeErrors({
      days: 7,
      content_type: selectedPromptType.value,
    });

    if (res.success) {
      analysisResult.value = res.data;
      newPromptDraft.value =
        extractCodeBlock(res.data.suggestions) ||
        "无法自动提取 Prompt 代码，请手动复制建议内容。";
    }
  } catch (e: unknown) {
    ElMessage.error("分析失败：" + (e.message || "未知错误"));
  } finally {
    analyzing.value = false;
  }
};

const applyOptimization = async () => {
  if (!newPromptDraft.value) return;
  if (!confirm("确定要更新线上 System Prompt 吗？此操作将记录在版本历史中。"))
    return;

  try {
    await adminAiApi.updatePrompt({
      prompt_type: selectedPromptType.value,
      new_prompt: newPromptDraft.value,
      update_reason:
        "基于元分析报告的自动进化 (v" + (totalVersions.value + 1) + ")",
    });
    ElMessage.success("更新成功！系统已进化。");
    analysisResult.value = null;
    fetchVersions();
  } catch (e) {
    ElMessage.error("更新失败");
  }
};

// Manual Correction
const openCorrectionDialog = () => {
  correctionDialogVisible.value = true;
};

const submitCorrection = async () => {
  try {
    await adminAiApi.submitCorrection({
      type: correctionForm.value.type,
      content: correctionForm.value.content,
      original_score: correctionForm.value.originalScore,
      corrected_score: correctionForm.value.correctedScore,
      reason: correctionForm.value.reason
    });
    ElMessage.success("修正已提交！系统将在下次元分析时学习此案例。");
    correctionDialogVisible.value = false;
    totalCorrections.value++;
    // 重置表单
    correctionForm.value = {
      type: "COMMENT",
      content: "",
      originalScore: 0,
      correctedScore: 100,
      reason: ""
    };
  } catch (e) {
    ElMessage.error("提交失败");
  }
};

// Utils
const renderMarkdown = (text: string) => {
  if (!text) return "";
  return text.replace(/\n/g, "<br>").replace(/\*\*(.*?)\*\*/g, "<b>$1</b>");
};

const extractCodeBlock = (text: string) => {
  if (!text) return "";
  const match = text.match(/```.*?\n([\s\S]*?)```/);
  return match ? match[1] : "";
};

onMounted(() => {
  fetchVersions();
});
</script>

<style scoped lang="scss">
.ai-governance-container {
  padding: var(--space-6);
  background: var(--bg-global);
  min-height: 100vh;
}

.header-section {
  margin-bottom: var(--space-6);
  h2 {
    font-size: var(--font-size-2xl);
    margin-bottom: var(--space-2);
    color: var(--text-primary);
    display: flex;
    align-items: center;
    gap: var(--space-2);
  }
  .subtitle {
    color: var(--text-secondary);
  }
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-5);
  margin-bottom: var(--space-6);

  .stat-card {
    background: var(--bg-white);
    padding: var(--space-5);
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow-card);

    &.warning {
      border-left: 4px solid var(--warning-color);
    }

    .label {
      font-size: var(--font-size-sm);
      color: var(--text-tertiary);
      margin-bottom: var(--space-2);
    }
    .value {
      font-size: var(--font-size-3xl);
      font-weight: var(--font-weight-bold);
      color: var(--text-primary);
    }
    .unit {
      font-size: var(--font-size-sm);
      font-weight: normal;
    }
    .desc {
      font-size: 12px;
      color: #aaa;
      margin-top: 4px;
    }

    .action button {
      background: linear-gradient(135deg, #667eea, #764ba2);
      color: white;
      border: none;
      padding: 8px 16px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 14px;
      width: 100%;
      margin-top: 10px;

      &:disabled {
        opacity: 0.7;
        cursor: not-allowed;
      }
    }
  }
}

.main-content {
  display: grid;
  grid-template-columns: 350px 1fr;
  gap: 24px;
  height: 600px;
}

.panel {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  overflow: hidden;

  .panel-header {
    padding: 16px;
    border-bottom: 1px solid #eee;
    display: flex;
    justify-content: space-between;
    align-items: center;
    h3 {
      margin: 0;
      font-size: 16px;
    }
    select {
      padding: 4px;
      border: 1px solid #ddd;
      border-radius: 4px;
    }
  }
}

.evolution-panel {
  .timeline {
    flex: 1;
    overflow-y: auto;
    padding: 16px;

    .timeline-item {
      padding: 12px;
      border-left: 2px solid #ddd;
      margin-left: 8px;
      position: relative;
      cursor: pointer;
      transition: all 0.2s;

      &:hover {
        background: #f5f5f5;
      }
      &.active {
        border-left-color: #764ba2;
        background: #f0f4ff;
      }

      &::before {
        content: "";
        position: absolute;
        left: -5px;
        top: 18px;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #ddd;
      }
      &.active::before {
        background: #764ba2;
      }

      .time {
        font-size: 12px;
        color: #999;
      }
      .reason {
        font-size: 14px;
        margin: 4px 0;
        font-weight: 500;
      }
      .meta {
        font-size: 12px;
        color: #bbb;
      }
    }
  }
}

.detail-panel {
  .version-detail,
  .analysis-result {
    padding: 24px;
    height: 100%;
    display: flex;
    flex-direction: column;
  }

  .detail-header,
  .result-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    
    .actions {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .tag {
      background: #e0e7ff;
      color: #4338ca;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 12px;
    }
  }

  .code-preview {
    flex: 1;
    background: #2d2d2d;
    color: #ccc;
    padding: 16px;
    border-radius: 8px;
    overflow: auto;
    pre {
      margin: 0;
      font-family: monospace;
      white-space: pre-wrap;
    }
  }
  
  /* Diff View Styles */
  .diff-view {
    flex: 1;
    display: flex;
    gap: 12px;
    overflow: hidden;
    
    .diff-column {
      flex: 1;
      display: flex;
      flex-direction: column;
      background: #f8f9fa;
      border: 1px solid #ddd;
      border-radius: 6px;
      overflow: hidden;
      
      &.current {
        background: #fff;
        border-color: #764ba2;
      }
      
      .diff-header {
        padding: 8px;
        background: #eee;
        font-size: 12px;
        font-weight: bold;
        border-bottom: 1px solid #ddd;
      }
      
      pre {
        flex: 1;
        margin: 0;
        padding: 12px;
        overflow: auto;
        font-size: 12px;
        white-space: pre-wrap;
        font-family: monospace;
      }
    }
  }

  .analysis-content {
    flex: 1;
    overflow-y: auto;
    border: 1px solid #eee;
    padding: 16px;
    border-radius: 8px;
    margin-bottom: 16px;
  }

  .prompt-editor {
    width: 100%;
    height: 150px;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 12px;
    font-family: monospace;
    margin-bottom: 12px;
  }

  .btn-group {
    display: flex;
    gap: 12px;
    justify-content: flex-end;
    button {
      padding: 8px 24px;
      border-radius: 6px;
      border: none;
      cursor: pointer;
      &.secondary {
        background: #eee;
        color: #666;
      }
      &.primary {
        background: #764ba2;
        color: white;
      }
    }
  }
}
</style>