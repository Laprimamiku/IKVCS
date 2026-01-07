<template>
  <div class="ai-governance-container">
    <div class="header-section">
      <h2>
        <el-icon><Setting /></el-icon>
        AI 智能治理中心
      </h2>
      <p class="subtitle">
        监控 AI 系统运行状态，管理 Prompt 版本迭代与智能体优化策略。
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
      <!-- 左侧：Prompt版本管理 -->
      <div class="panel evolution-panel">
        <div class="panel-header">
          <h3>
            <el-icon><Document /></el-icon>
            Prompt 版本管理
          </h3>
          <el-select v-model="selectedPromptType" @change="fetchVersions" size="small" style="width: 200px;">
            <el-option label="评论区审核" value="COMMENT" />
            <el-option label="弹幕审核" value="DANMAKU" />
          </el-select>
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
            <div class="meta">
              <el-tag v-if="version.is_active" type="success" size="small">激活中</el-tag>
              <span class="operator">Operator ID: {{ version.updated_by }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：详情面板 -->
      <div class="panel detail-panel">
        <!-- 版本详情视图 -->
        <div v-if="selectedVersion && !analysisResult && !showShadowTest && !showCostDashboard" class="version-detail">
          <div class="detail-header">
            <h3>版本 V{{ selectedVersion.id }} 详情</h3>
            <div class="actions">
              <el-button type="primary" size="small" @click="showShadowTest = true">
                <el-icon><DataAnalysis /></el-icon> Shadow 测试
              </el-button>
              <el-button type="info" size="small" @click="showCostDashboard = true">
                <el-icon><TrendCharts /></el-icon> 成本仪表盘
              </el-button>
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

        <!-- Shadow测试视图 -->
        <div v-if="showShadowTest" class="shadow-test-view">
          <div class="result-header">
            <h3>
              <el-icon><DataAnalysis /></el-icon>
              Shadow 测试
            </h3>
            <el-button type="info" size="small" @click="showShadowTest = false">
              返回
            </el-button>
          </div>

          <div class="shadow-test-content">
            <div class="test-config">
              <h4>测试配置</h4>
              <el-form :model="shadowTestForm" label-width="120px" size="small">
                <el-form-item label="候选版本">
                  <el-select v-model="shadowTestForm.candidateVersionId" placeholder="选择候选版本">
                    <el-option 
                      v-for="version in versions.filter(v => !v.is_active)" 
                      :key="version.id"
                      :label="`V${version.id} - ${version.update_reason}`"
                      :value="version.id"
                    />
                  </el-select>
                </el-form-item>
                <el-form-item label="测试样本数">
                  <el-input-number v-model="shadowTestForm.sampleLimit" :min="10" :max="200" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="runShadowTest" :loading="shadowTestLoading">
                    <el-icon><VideoPlay /></el-icon> 运行测试
                  </el-button>
                </el-form-item>
              </el-form>
            </div>

            <div v-if="shadowTestResults" class="test-results">
              <h4>测试结果</h4>
              <div class="metrics-grid">
                <div class="metric-card">
                  <div class="metric-label">一致率</div>
                  <div class="metric-value">{{ (shadowTestResults.consistency_rate * 100).toFixed(1) }}%</div>
                </div>
                <div class="metric-card">
                  <div class="metric-label">平均分数差异</div>
                  <div class="metric-value">{{ shadowTestResults.avg_score_diff.toFixed(1) }}</div>
                </div>
                <div class="metric-card">
                  <div class="metric-label">预计成本</div>
                  <div class="metric-value">¥{{ shadowTestResults.estimated_cost.toFixed(3) }}</div>
                </div>
                <div class="metric-card">
                  <div class="metric-label">样本数量</div>
                  <div class="metric-value">{{ shadowTestResults.sample_count }}</div>
                </div>
              </div>
              
              <div class="test-recommendation">
                <el-alert
                  :title="getTestRecommendation(shadowTestResults)"
                  :type="getTestRecommendationType(shadowTestResults)"
                  show-icon
                  :closable="false"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- 成本仪表盘视图 -->
        <div v-if="showCostDashboard" class="cost-dashboard-view">
          <div class="result-header">
            <h3>
              <el-icon><TrendCharts /></el-icon>
              成本与性能仪表盘
            </h3>
            <el-button type="info" size="small" @click="showCostDashboard = false">
              返回
            </el-button>
          </div>

          <div class="dashboard-content">
            <!-- Token预算状态 -->
            <div class="budget-section">
              <h4>Token 预算状态</h4>
              <div class="budget-cards">
                <div class="budget-card">
                  <div class="budget-header">
                    <span>每日预算</span>
                    <el-tag :type="getBudgetTagType(budgetStatus?.daily?.usage_rate || 0)">
                      {{ ((budgetStatus?.daily?.usage_rate || 0) * 100).toFixed(1) }}%
                    </el-tag>
                  </div>
                  <el-progress 
                    :percentage="(budgetStatus?.daily?.usage_rate || 0) * 100"
                    :color="getBudgetColor(budgetStatus?.daily?.usage_rate || 0)"
                  />
                  <div class="budget-details">
                    已用: {{ budgetStatus?.daily?.used || 0 }} / {{ budgetStatus?.daily?.limit || 0 }}
                  </div>
                </div>
                
                <div class="budget-card">
                  <div class="budget-header">
                    <span>每小时预算</span>
                    <el-tag :type="getBudgetTagType(budgetStatus?.hourly?.usage_rate || 0)">
                      {{ ((budgetStatus?.hourly?.usage_rate || 0) * 100).toFixed(1) }}%
                    </el-tag>
                  </div>
                  <el-progress 
                    :percentage="(budgetStatus?.hourly?.usage_rate || 0) * 100"
                    :color="getBudgetColor(budgetStatus?.hourly?.usage_rate || 0)"
                  />
                  <div class="budget-details">
                    已用: {{ budgetStatus?.hourly?.used || 0 }} / {{ budgetStatus?.hourly?.limit || 0 }}
                  </div>
                </div>
              </div>
            </div>

            <!-- 命中率统计 -->
            <div class="metrics-section">
              <h4>AI 处理命中率统计</h4>
              <div class="metrics-chart">
                <div class="chart-item" v-for="(value, key) in aiMetrics" :key="key">
                  <div class="chart-label">{{ getMetricLabel(key) }}</div>
                  <div class="chart-bar">
                    <div 
                      class="chart-fill" 
                      :style="{ width: getMetricPercentage(key, value) + '%' }"
                    ></div>
                  </div>
                  <div class="chart-value">{{ value }}</div>
                </div>
              </div>
            </div>

            <!-- 优化建议 -->
            <div class="optimization-section">
              <h4>优化建议</h4>
              <div class="optimization-cards">
                <el-card v-for="suggestion in optimizationSuggestions" :key="suggestion.type" class="suggestion-card">
                  <div class="suggestion-header">
                    <el-icon :class="suggestion.icon" />
                    <span>{{ suggestion.title }}</span>
                  </div>
                  <p>{{ suggestion.description }}</p>
                  <div class="suggestion-impact">
                    预计节省: <strong>{{ suggestion.impact }}</strong>
                  </div>
                </el-card>
              </div>
            </div>
          </div>
        </div>

        <!-- 错误分析结果视图 -->
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
import { Edit, Search, Setting, MagicStick, Document, DataAnalysis, TrendCharts, VideoPlay } from "@element-plus/icons-vue";
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

// 新增：Shadow测试相关状态
const showShadowTest = ref(false);
const shadowTestLoading = ref(false);
const shadowTestForm = ref({
  candidateVersionId: null,
  sampleLimit: 50
});
const shadowTestResults = ref(null);

// 新增：成本仪表盘相关状态
const showCostDashboard = ref(false);
const budgetStatus = ref(null);
const aiMetrics = ref({});
const optimizationSuggestions = ref([
  {
    type: 'cache',
    title: '提高缓存命中率',
    description: '当前缓存命中率较低，建议优化缓存策略以减少重复计算',
    impact: '30% Token消耗',
    icon: 'el-icon-lightning'
  },
  {
    type: 'sampling',
    title: '优化采样策略',
    description: '对低风险内容采用更激进的采样策略，减少不必要的分析',
    impact: '20% 处理时间',
    icon: 'el-icon-data-analysis'
  },
  {
    type: 'batch',
    title: '启用批量处理',
    description: '将相似内容批量处理，提高API调用效率',
    impact: '15% API调用',
    icon: 'el-icon-collection'
  }
]);

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

// 新增：Shadow测试方法
const runShadowTest = async () => {
  if (!shadowTestForm.value.candidateVersionId) {
    ElMessage.warning("请选择候选版本");
    return;
  }

  shadowTestLoading.value = true;
  try {
    const res = await adminAiApi.shadowTestPrompt({
      candidate_version_id: shadowTestForm.value.candidateVersionId,
      sample_limit: shadowTestForm.value.sampleLimit
    });

    if (res.success) {
      shadowTestResults.value = res.data;
      ElMessage.success("Shadow测试完成");
    }
  } catch (e) {
    ElMessage.error("Shadow测试失败");
  } finally {
    shadowTestLoading.value = false;
  }
};

const getTestRecommendation = (results) => {
  const consistencyRate = results.consistency_rate;
  const avgDiff = results.avg_score_diff;
  
  if (consistencyRate > 0.9 && avgDiff < 5) {
    return "建议发布：候选版本表现优秀，与当前版本高度一致";
  } else if (consistencyRate > 0.8 && avgDiff < 10) {
    return "谨慎发布：候选版本表现良好，但存在一定差异，建议进一步测试";
  } else {
    return "不建议发布：候选版本与当前版本差异较大，需要进一步优化";
  }
};

const getTestRecommendationType = (results) => {
  const consistencyRate = results.consistency_rate;
  if (consistencyRate > 0.9) return "success";
  if (consistencyRate > 0.8) return "warning";
  return "error";
};

// 新增：成本仪表盘方法
const fetchBudgetStatus = async () => {
  try {
    // 这里应该调用实际的API获取预算状态
    // 暂时使用模拟数据
    budgetStatus.value = {
      daily: { used: 650, limit: 1000, usage_rate: 0.65 },
      hourly: { used: 45, limit: 100, usage_rate: 0.45 }
    };
  } catch (e) {
    console.error("获取预算状态失败", e);
  }
};

const fetchAiMetrics = async () => {
  try {
    const res = await adminAiApi.getAiMetrics();
    if (res.success) {
      aiMetrics.value = res.data.metrics;
    }
  } catch (e) {
    console.error("获取AI指标失败", e);
  }
};

const getBudgetTagType = (rate) => {
  if (rate > 0.8) return "danger";
  if (rate > 0.6) return "warning";
  return "success";
};

const getBudgetColor = (rate) => {
  if (rate > 0.8) return "#f56c6c";
  if (rate > 0.6) return "#e6a23c";
  return "#67c23a";
};

const getMetricLabel = (key) => {
  const labels = {
    rule_hit: "规则命中",
    exact_hit: "精确缓存",
    semantic_hit: "语义缓存",
    cloud_call: "云端调用",
    local_call: "本地调用",
    jury_call: "陪审团调用"
  };
  return labels[key] || key;
};

const getMetricPercentage = (key, value) => {
  const total = Object.values(aiMetrics.value).reduce((sum, val) => sum + val, 0);
  return total > 0 ? (value / total * 100) : 0;
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
  fetchBudgetStatus();
  fetchAiMetrics();
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
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-5);
  margin-bottom: var(--space-6);

  .stat-card {
    background: var(--bg-white);
    padding: var(--space-5);
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow-card);
    transition: transform 0.2s, box-shadow 0.2s;
    
    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }

    &.warning {
      border-left: 4px solid var(--warning-color);
    }

    .label {
      font-size: var(--font-size-sm);
      color: var(--text-tertiary);
      margin-bottom: var(--space-2);
      font-weight: var(--font-weight-medium);
    }
    .value {
      font-size: var(--font-size-3xl);
      font-weight: var(--font-weight-bold);
      color: var(--text-primary);
      margin-bottom: var(--space-2);
    }
    .unit {
      font-size: var(--font-size-sm);
      font-weight: normal;
      color: var(--text-secondary);
    }
    .desc {
      font-size: 12px;
      color: var(--text-tertiary);
      margin-top: var(--space-2);
    }

    .action {
      margin-top: var(--space-3);
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
  transition: box-shadow 0.2s;
  
  &:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  .panel-header {
    padding: var(--space-4);
    border-bottom: 1px solid var(--border-light);
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--bg-hover);
    
    h3 {
      display: flex;
      align-items: center;
      gap: var(--space-2);
      margin: 0;
      font-size: var(--font-size-lg);
      font-weight: var(--font-weight-semibold);
      color: var(--text-primary);
    }
  }
}

.evolution-panel {
  .timeline {
    flex: 1;
    overflow-y: auto;
    padding: 16px;

    .timeline-item {
      padding: var(--space-3);
      border-left: 3px solid var(--border-color);
      margin-left: var(--space-2);
      position: relative;
      cursor: pointer;
      transition: all 0.2s;
      border-radius: var(--radius-sm);
      margin-bottom: var(--space-2);

      &:hover {
        background: var(--bg-hover);
        border-left-color: var(--primary-color);
      }
      &.active {
        border-left-color: var(--primary-color);
        background: var(--bg-primary-light);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
      }

      &::before {
        content: "";
        position: absolute;
        left: -6px;
        top: 20px;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: var(--border-color);
        border: 2px solid white;
        transition: all 0.2s;
      }
      &.active::before {
        background: var(--primary-color);
        border-color: var(--primary-color);
        box-shadow: 0 0 0 3px rgba(118, 75, 162, 0.2);
      }

      .time {
        font-size: var(--font-size-xs);
        color: var(--text-tertiary);
        margin-bottom: var(--space-1);
      }
      .reason {
        font-size: var(--font-size-sm);
        margin: var(--space-1) 0;
        font-weight: var(--font-weight-medium);
        color: var(--text-primary);
      }
      .meta {
        font-size: var(--font-size-xs);
        color: var(--text-tertiary);
        margin-top: var(--space-1);
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

/* 新增：Shadow测试样式 */
.shadow-test-view {
  padding: 24px;
  height: 100%;
  display: flex;
  flex-direction: column;
  
  .test-config {
    margin-bottom: 24px;
    padding: 16px;
    background: var(--bg-gray-1);
    border-radius: 8px;
    
    h4 {
      margin: 0 0 16px 0;
      color: var(--text-primary);
    }
  }
  
  .test-results {
    flex: 1;
    
    h4 {
      margin: 0 0 16px 0;
      color: var(--text-primary);
    }
    
    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 16px;
      margin-bottom: 20px;
      
      .metric-card {
        background: white;
        padding: 16px;
        border-radius: 8px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        
        .metric-label {
          font-size: 12px;
          color: var(--text-tertiary);
          margin-bottom: 8px;
        }
        
        .metric-value {
          font-size: 24px;
          font-weight: bold;
          color: var(--text-primary);
        }
      }
    }
    
    .test-recommendation {
      margin-top: 16px;
    }
  }
}

/* 新增：成本仪表盘样式 */
.cost-dashboard-view {
  padding: 24px;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  
  .dashboard-content {
    flex: 1;
    
    h4 {
      margin: 0 0 16px 0;
      color: var(--text-primary);
      font-size: 16px;
    }
  }
  
  .budget-section {
    margin-bottom: 32px;
    
    .budget-cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 20px;
      
      .budget-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        
        .budget-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 12px;
          
          span {
            font-weight: 600;
            color: var(--text-primary);
          }
        }
        
        .budget-details {
          margin-top: 8px;
          font-size: 12px;
          color: var(--text-tertiary);
        }
      }
    }
  }
  
  .metrics-section {
    margin-bottom: 32px;
    
    .metrics-chart {
      background: white;
      padding: 20px;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      
      .chart-item {
        display: flex;
        align-items: center;
        margin-bottom: 16px;
        
        &:last-child {
          margin-bottom: 0;
        }
        
        .chart-label {
          width: 100px;
          font-size: 14px;
          color: var(--text-secondary);
        }
        
        .chart-bar {
          flex: 1;
          height: 20px;
          background: var(--bg-gray-1);
          border-radius: 10px;
          margin: 0 16px;
          position: relative;
          overflow: hidden;
          
          .chart-fill {
            height: 100%;
            background: linear-gradient(90deg, #409EFF, #67C23A);
            border-radius: 10px;
            transition: width 0.3s ease;
          }
        }
        
        .chart-value {
          width: 60px;
          text-align: right;
          font-weight: 600;
          color: var(--text-primary);
        }
      }
    }
  }
  
  .optimization-section {
    .optimization-cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
      
      .suggestion-card {
        .suggestion-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 12px;
          font-weight: 600;
          color: var(--text-primary);
        }
        
        p {
          margin: 0 0 12px 0;
          color: var(--text-secondary);
          line-height: 1.5;
        }
        
        .suggestion-impact {
          font-size: 12px;
          color: var(--success-color);
          
          strong {
            color: var(--success-color);
          }
        }
      }
    }
  }
}
</style>
