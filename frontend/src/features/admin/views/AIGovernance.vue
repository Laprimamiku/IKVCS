<template>
  <div class="ai-governance-container">
    <div class="header-section">
      <h2>🤖 AI 进化控制台</h2>
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
            {{ analyzing ? "分析中..." : "✨ 触发元分析" }}
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
            <span class="tag">{{ selectedVersion.prompt_type }}</span>
          </div>
          <div class="code-preview">
            <pre>{{ selectedVersion.prompt_content }}</pre>
          </div>
        </div>

        <div v-if="analysisResult" class="analysis-result">
          <div class="result-header">
            <h3>🔍 错误模式元分析报告</h3>
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import {
  adminAiApi,
  type PromptVersion,
  type ErrorPatternAnalysis,
} from "../api/admin.api";
import { formatDate } from "@/shared/utils/formatters"; // 假设你有这个工具函数

// 状态
const versions = ref<PromptVersion[]>([]);
const totalVersions = ref(0);
const lastUpdateTime = ref("-");
const selectedPromptType = ref("COMMENT");
const selectedVersion = ref<PromptVersion | null>(null);

const pendingCorrections = ref(12); // 示例数据，实际可调用 getCorrections 统计
const analyzing = ref(false);
const analysisResult = ref<ErrorPatternAnalysis | null>(null);
const newPromptDraft = ref("");

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

const triggerAnalysis = async () => {
  analyzing.value = true;
  try {
    const res = await adminAiApi.analyzeErrors({
      days: 7,
      content_type: selectedPromptType.value,
    });

    if (res.success) {
      analysisResult.value = res.data;
      // 提取建议作为草稿
      newPromptDraft.value =
        extractCodeBlock(res.data.suggestions) ||
        "无法自动提取 Prompt 代码，请手动复制建议内容。";
    }
  } catch (e) {
    alert("分析失败：" + (e as any).message);
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
    alert("更新成功！系统已进化。");
    analysisResult.value = null;
    fetchVersions(); // 刷新列表
  } catch (e) {
    alert("更新失败");
  }
};

// 简单的 Markdown 渲染模拟 (生产环境建议用 markdown-it)
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
  padding: 24px;
  background: #f8f9fa;
  min-height: 100vh;
}

.header-section {
  margin-bottom: 24px;
  h2 {
    font-size: 24px;
    margin-bottom: 8px;
  }
  .subtitle {
    color: #666;
  }
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 24px;

  .stat-card {
    background: white;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);

    &.warning {
      border-left: 4px solid #ff9800;
    }

    .label {
      font-size: 14px;
      color: #888;
      margin-bottom: 8px;
    }
    .value {
      font-size: 28px;
      font-weight: bold;
      color: #333;
    }
    .unit {
      font-size: 14px;
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
