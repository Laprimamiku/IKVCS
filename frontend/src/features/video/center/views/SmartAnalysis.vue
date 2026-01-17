<template>
  <div class="smart-analysis">
    <div class="page-header">
      <div>
        <h2>智能分析报告</h2>
        <p>基于AI的互动内容质量治理/自动审核与高亮</p>
      </div>
      <div class="header-actions">
        <el-tag v-if="progress && progress.status && progress.status !== 'idle'" type="info" effect="plain">
          分析中 {{ progress.status }} {{ progress.progress ?? 0 }}%
        </el-tag>
        <el-tooltip content="重新计算：对最近200条互动内容重新进行AI分析，更新评分和分类" placement="bottom">
          <el-button :loading="recomputeLoading" @click="triggerRecompute">
            <el-icon><Refresh /></el-icon>
            重新计算
          </el-button>
        </el-tooltip>
        <el-tooltip content="触发陪审团分析：使用多智能体系统对最近100条内容进行深度复核，提高分析准确性" placement="bottom">
          <el-button type="primary" :loading="juryLoading" @click="triggerJury">
            触发陪审团分析
          </el-button>
        </el-tooltip>
        <el-tooltip content="刷新：重新加载当前页面的分析数据" placement="bottom">
          <el-button type="primary" link @click="fetchData">刷新</el-button>
        </el-tooltip>
      </div>
    </div>

    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="5" animated />
    </div>

    <div v-else-if="error || !data" class="empty-state">
      <el-empty :description="error || '暂无数据'">
        <el-button type="primary" @click="fetchData">重试</el-button>
      </el-empty>
    </div>

    <div v-else class="content-grid">
      <el-card class="overview-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>治理总览</span>
            <el-tag size="small" type="success">实时数据</el-tag>
          </div>
        </template>

        <div class="overview-metrics">
          <div class="metric-item">
            <div class="metric-label">治理总分</div>
            <div class="metric-value">{{ overview.governance_score ?? 0 }}</div>
            <el-progress
              :percentage="overview.governance_score ?? 0"
              :color="getScoreColor(overview.governance_score ?? 0)"
              :stroke-width="8"
            />
          </div>
          <div class="metric-item">
            <div class="metric-label">质量分</div>
            <div class="metric-value">{{ overview.quality_score ?? 0 }}</div>
            <el-progress
              :percentage="overview.quality_score ?? 0"
              :color="getScoreColor(overview.quality_score ?? 0)"
              :stroke-width="8"
            />
          </div>
          <div class="metric-item">
            <div class="metric-label">风险分</div>
            <div class="metric-value">{{ overview.risk_score ?? 0 }}</div>
            <el-progress
              :percentage="overview.risk_score ?? 0"
              :color="getScoreColor(overview.risk_score ?? 0)"
              :stroke-width="8"
            />
          </div>
        </div>

        <div class="overview-tags">
          <el-tag>AI覆盖 {{ formatPercent(overview.ai_coverage_rate) }}</el-tag>
          <el-tag type="danger">风险率 {{ formatPercent(overview.risk_rate) }}</el-tag>
          <el-tag type="success">高质曝光 {{ formatPercent(overview.highlight_rate) }}</el-tag>
          <el-tag type="warning">低质率 {{ formatPercent(overview.low_quality_rate) }}</el-tag>
          <el-tag type="info">节省人工 {{ formatPercent(overview.auto_review_saving_rate) }}</el-tag>
        </div>
      </el-card>

      <el-card class="action-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>治理建议</span>
            <el-icon><InfoFilled /></el-icon>
          </div>
        </template>

        <div v-if="actions.length" class="actions-list">
          <el-alert
            v-for="(item, idx) in actions"
            :key="idx"
            :title="item.title"
            :description="item.detail"
            type="warning"
            :closable="false"
            show-icon
          />
        </div>
        <el-empty v-else description="暂无建议" />
      </el-card>

      <el-card class="distribution-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>质量分布</span>
            <el-tag size="small" type="info">分桶统计</el-tag>
          </div>
        </template>

        <div class="bucket-list">
          <div class="bucket-row">
            <span class="bucket-label">0-39</span>
            <el-progress
              :percentage="getBucketPercent(distribution['0_39'])"
              :color="'#F56C6C'"
              :format="() => `${distribution['0_39'] || 0} 条`"
            />
          </div>
          <div class="bucket-row">
            <span class="bucket-label">40-59</span>
            <el-progress
              :percentage="getBucketPercent(distribution['40_59'])"
              :color="'#E6A23C'"
              :format="() => `${distribution['40_59'] || 0} 条`"
            />
          </div>
          <div class="bucket-row">
            <span class="bucket-label">60-79</span>
            <el-progress
              :percentage="getBucketPercent(distribution['60_79'])"
              :color="'#409EFF'"
              :format="() => `${distribution['60_79'] || 0} 条`"
            />
          </div>
          <div class="bucket-row">
            <span class="bucket-label">80-100</span>
            <el-progress
              :percentage="getBucketPercent(distribution['80_100'])"
              :color="'#67C23A'"
              :format="() => `${distribution['80_100'] || 0} 条`"
            />
          </div>
        </div>
      </el-card>

      <el-card class="jury-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>多智能体陪审团</span>
            <div class="header-badges">
              <el-tag v-if="data.conflict_resolved" type="warning" effect="dark">
                <el-icon><ScaleToOriginal /></el-icon> Judge Agent 已介入
              </el-tag>
              <el-tag v-else type="success" effect="plain">一致通过</el-tag>
            </div>
          </div>
        </template>

        <div class="experts-container">
          <div
            v-for="(expert, index) in data.expert_results"
            :key="index"
            class="expert-item"
          >
            <div class="expert-avatar">
              <div class="avatar-circle" :class="getExpertClass(expert.agent)">
                {{ expert.agent.charAt(0) }}
              </div>
              <span class="expert-name">{{ expert.agent }}</span>
            </div>

            <div class="expert-score">
              <el-progress
                type="dashboard"
                :percentage="expert.score"
                :color="getScoreColor(expert.score)"
                :width="80"
              />
              <span class="score-label">评分</span>
            </div>

            <div class="expert-opinion">
              <div class="opinion-bubble">
                {{ expert.opinion }}
              </div>
            </div>
          </div>
        </div>

        <el-alert
          v-if="data.summary"
          :title="data.summary"
          type="info"
          show-icon
          :closable="false"
          class="insight-alert"
        />
      </el-card>

      <div class="right-panels">
        <el-card class="sentiment-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>情感分布</span>
              <el-tag type="success" size="small">统计</el-tag>
            </div>
          </template>

          <div class="sentiment-bars">
            <div class="bar-group">
              <div class="label">正面 (Positive)</div>
              <el-progress
                :percentage="calculatePercent(data.sentiment.positive)"
                :color="'#67C23A'"
                :format="() => data.sentiment.positive + ' 条'"
              />
            </div>
            <div class="bar-group">
              <div class="label">中性 (Neutral)</div>
              <el-progress
                :percentage="calculatePercent(data.sentiment.neutral)"
                :color="'#409EFF'"
                :format="() => data.sentiment.neutral + ' 条'"
              />
            </div>
            <div class="bar-group">
              <div class="label">负面 (Negative)</div>
              <el-progress
                :percentage="calculatePercent(data.sentiment.negative)"
                :color="'#F56C6C'"
                :format="() => data.sentiment.negative + ' 条'"
              />
            </div>
          </div>
        </el-card>

      </div>

      <el-card class="highlight-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>高质量内容曝光</span>
            <el-tag type="success" size="small">优先展示</el-tag>
          </div>
        </template>

        <el-table :data="highlightItems" style="width: 100%" stripe v-loading="highlightUpdating">
          <el-table-column prop="content" label="内容" min-width="200" show-overflow-tooltip />
          <el-table-column prop="type" label="类型" width="90">
            <template #default="scope">
              <el-tag size="small" :type="scope.row.type === 'danmaku' ? 'primary' : 'success'">
                {{ scope.row.type === 'danmaku' ? '弹幕' : '评论' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="score" label="评分" width="90" align="center">
            <template #default="scope">
              <span :style="{ color: getScoreColor(scope.row.score), fontWeight: '600' }">
                {{ scope.row.score }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="reason" label="理由" width="180" show-overflow-tooltip />
          <el-table-column prop="source" label="来源" width="120">
            <template #default="scope">
              <el-tag size="small" :type="getSourceTagType(scope.row.source)">
                {{ getSourceLabel(scope.row.source) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="time" label="时间" width="180">
            <template #default="scope">
              {{ formatTime(scope.row.time) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="scope">
              <el-switch
                v-model="scope.row.is_highlight"
                :loading="scope.row.updating"
                active-text="高亮"
                inactive-text="普通"
                @change="handleHighlightToggle(scope.row)"
                :disabled="scope.row.type === 'comment'"
              />
            </template>
          </el-table-column>
        </el-table>

        <el-empty v-if="!highlightItems.length" description="暂无高质量内容" />
      </el-card>

      <el-card class="risk-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>风险/违规内容 (AI预警)</span>
            <el-button type="primary" link @click="fetchData">刷新</el-button>
          </div>
        </template>

        <el-table :data="data.risks" style="width: 100%" stripe>
          <el-table-column prop="content" label="内容" min-width="200" />
          <el-table-column prop="reason" label="原因" width="150">
            <template #default="scope">
              <el-tag type="danger">{{ scope.row.reason }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="score" label="AI评分" width="100">
            <template #default="scope">
              <span style="color: #f56c6c; font-weight: bold">{{ scope.row.score }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="time" label="时间" width="180">
            <template #default="scope">
              {{ formatTime(scope.row.time) }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed } from "vue";
import { useRoute } from "vue-router";
import { videoApi } from "@/features/video/shared/api/video.api";
import { ElMessage } from "element-plus";
import { ScaleToOriginal, InfoFilled, Refresh } from "@element-plus/icons-vue";

const route = useRoute();
const loading = ref(true);
const error = ref("");
const data = ref<any>(null);
const juryLoading = ref(false);
const recomputeLoading = ref(false);
const progress = ref<any>(null);
const highlightUpdating = ref(false);
const managementLoading = ref(false);
const managementItems = ref<any[]>([]);
const managementPage = ref(1);
const managementTotal = ref(0);
const managementFilters = ref({
  item_type: "",
  filter: "",
  score_gt: undefined as number | undefined,
  score_lt: undefined as number | undefined,
});
let progressTimer: number | null = null;

const governance = computed(() => data.value?.governance || {});
const overview = computed(() => governance.value?.overview || {});
const distribution = computed(() => governance.value?.distribution?.score_buckets || {});
const highlightItems = computed(() => governance.value?.exposure?.items || []);
const actions = computed(() => governance.value?.actions || []);

// 总数计算
const totalCount = computed(() => {
  if (!data.value?.sentiment) return 0;
  return (
    data.value.sentiment.positive +
    data.value.sentiment.neutral +
    data.value.sentiment.negative
  );
});

const calculatePercent = (val: number) => {
  if (!totalCount.value) return 0;
  return Math.round((val / totalCount.value) * 100);
};

const getBucketPercent = (val: number) => {
  if (!totalCount.value) return 0;
  return Math.round(((val || 0) / totalCount.value) * 100);
};

const formatPercent = (value: number) => {
  const safe = Number.isFinite(value) ? value : 0;
  return `${(safe * 100).toFixed(1)}%`;
};

const formatTime = (timeStr: string) => {
  if (!timeStr) return "-";
  return new Date(timeStr).toLocaleString();
};

const getExpertClass = (agentName: string) => {
  if (agentName.includes("Meme")) return "meme-expert";
  if (agentName.includes("Emotion")) return "emotion-expert";
  if (agentName.includes("Legal")) return "legal-expert";
  return "default-expert";
};

const getScoreColor = (score: number) => {
  if (score >= 90) return "#67C23A";
  if (score >= 60) return "#E6A23C";
  return "#F56C6C";
};

const getSourceTagType = (source: string) => {
  switch (source) {
    case "cache_exact":
    case "cache_semantic":
      return "success";
    case "cloud_llm":
      return "warning";
    case "local_model":
      return "info";
    case "multi_agent":
      return "danger";
    case "rule_hit":
      return "primary";
    default:
      return "";
  }
};

const getSourceLabel = (source: string) => {
  const labels: Record<string, string> = {
    cache_exact: "精确缓存",
    cache_semantic: "语义缓存",
    cloud_llm: "云端模型",
    local_model: "本地模型",
    multi_agent: "多智能体",
    rule_hit: "规则命中",
    default: "默认",
    unknown: "未知",
  };
  return labels[source] || source;
};

const getAblationLabel = (key: string) => {
  const labels: Record<string, string> = {
    rule_filter: "规则过滤",
    exact_cache: "精确缓存",
    semantic_cache: "语义缓存",
    local_model: "本地模型",
    cloud_model: "云端模型",
    multi_agent: "多智能体",
    queue_enabled: "队列分析",
    token_saving: "Token优化",
  };
  return labels[key] || key;
};

const handleHighlightToggle = async (item: any) => {
  if (item.type === "comment") {
    ElMessage.warning("评论的高亮状态由AI评分决定，暂不支持手动修改");
    // 恢复原状态
    item.is_highlight = !item.is_highlight;
    return;
  }

  const videoId = Number(route.params.videoId);
  if (!videoId || !item.id) {
    ElMessage.error("参数错误");
    item.is_highlight = !item.is_highlight; // 恢复原状态
    return;
  }

  item.updating = true;
  try {
    const res = await videoApi.updateHighlightStatus(
      videoId,
      item.type,
      item.id,
      item.is_highlight
    );
    if (res.success) {
      ElMessage.success(item.is_highlight ? "已标记为高质量内容" : "已取消高质量标记");
      // 刷新数据以更新统计
      await fetchData();
    } else {
      ElMessage.error(res.message || "更新失败");
      item.is_highlight = !item.is_highlight; // 恢复原状态
    }
  } catch (err: any) {
    console.error("更新高亮状态失败:", err);
    ElMessage.error(err.response?.data?.detail || "更新失败，请稍后重试");
    item.is_highlight = !item.is_highlight; // 恢复原状态
  } finally {
    item.updating = false;
  }
};

const fetchData = async () => {
  const videoId = Number(route.params.videoId);
  if (!videoId) {
    error.value = "无效的视频ID";
    loading.value = false;
    return;
  }

  loading.value = true;
  error.value = "";

  try {
    const res = await videoApi.getAnalysis(videoId);
    if (res.success) {
      data.value = res.data;
    } else {
      error.value = res.message || "获取数据失败";
    }
  } catch (err: unknown) {
    console.error(err);
    if (err.response?.status === 401) {
      error.value = "未授权访问";
      ElMessage.warning("请登录");
    } else {
      error.value = "获取分析数据失败";
    }
  } finally {
    loading.value = false;
  }
};

const fetchProgress = async () => {
  const videoId = Number(route.params.videoId);
  if (!videoId) return;
  try {
    const res = await videoApi.getAnalysisProgress(videoId);
    if (res.success) progress.value = res.data;
  } catch (err) {
    console.error(err);
  }
};

const triggerRecompute = async () => {
  const videoId = Number(route.params.videoId);
  if (!videoId) {
    ElMessage.error("无效的视频ID");
    return;
  }
  recomputeLoading.value = true;
  try {
    const res = await videoApi.triggerAnalysisRecompute(videoId, { scope: "recent", limit: 200 });
    if (res.success) {
      ElMessage.success(res.message || "重新计算已启动");
      await fetchProgress();

      if (progressTimer) window.clearInterval(progressTimer);
      progressTimer = window.setInterval(async () => {
        await fetchProgress();
        if (progress.value?.status === "idle") {
          if (progressTimer) window.clearInterval(progressTimer);
          progressTimer = null;
        }
      }, 1500);
    } else {
      ElMessage.error(res.message || "启动失败");
    }
  } catch (err) {
    console.error(err);
    ElMessage.error("触发重新计算失败");
  } finally {
    recomputeLoading.value = false;
  }
};

const triggerJury = async () => {
  const videoId = Number(route.params.videoId);
  if (!videoId) {
    ElMessage.error("无效的视频ID");
    return;
  }
  juryLoading.value = true;
  try {
    const res = await videoApi.triggerJuryReview(videoId, { scope: "recent", limit: 100 });
    if (res.success) {
      ElMessage.success(res.message || "陪审团分析已启动");
      fetchData();
    } else {
      ElMessage.error(res.message || "启动失败");
    }
  } catch (err) {
    console.error(err);
    ElMessage.error("触发陪审团分析失败");
  } finally {
    juryLoading.value = false;
  }
};

const fetchManagementItems = async () => {
  const videoId = Number(route.params.videoId);
  if (!videoId) return;

  managementLoading.value = true;
  try {
    const params: any = {
      page: managementPage.value,
      page_size: 5,
    };
    if (managementFilters.value.item_type) {
      params.item_type = managementFilters.value.item_type;
    }
    if (managementFilters.value.filter) {
      params.filter = managementFilters.value.filter;
    }
    if (managementFilters.value.score_gt !== undefined) {
      params.score_gt = managementFilters.value.score_gt;
    }
    if (managementFilters.value.score_lt !== undefined) {
      params.score_lt = managementFilters.value.score_lt;
    }

    const res = await videoApi.getAnalysisItems(videoId, params);
    if (res.success && res.data) {
      managementItems.value = res.data.items || [];
      managementTotal.value = res.data.total || 0;
      // 为每个item添加updating标记
      managementItems.value.forEach((item: any) => {
        item.updating = false;
      });
    } else {
      ElMessage.error(res.message || "获取数据失败");
    }
  } catch (err: any) {
    console.error("获取互动管理数据失败:", err);
    ElMessage.error("获取数据失败");
  } finally {
    managementLoading.value = false;
  }
};

onMounted(() => {
  fetchData();
  fetchProgress();
  fetchManagementItems();
});

onBeforeUnmount(() => {
  if (progressTimer) window.clearInterval(progressTimer);
  progressTimer = null;
});
</script>

<style scoped lang="scss">
.smart-analysis {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  h2 {
    font-size: 24px;
    margin: 0 0 8px 0;
    color: #18191c;
  }
  p {
    color: #61666d;
    font-size: 14px;
    margin: 0;
  }
  .header-actions {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
  }
}

.content-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-lg);
}

.header-badges {
  display: flex;
  gap: var(--space-2);
}

.overview-card {
  border-radius: 12px;
}

.overview-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.metric-item {
  background: linear-gradient(135deg, #f5f7fa 0%, #e9ecef 100%);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: transform 0.2s, box-shadow 0.2s;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }
}

.metric-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.metric-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}

.overview-tags {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  padding-top: 16px;
  border-top: 1px solid var(--border-light);
  
  .el-tag {
    font-size: 12px;
    padding: 6px 12px;
    border-radius: 6px;
  }
}

.action-card {
  border-radius: 12px;
}

.actions-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.distribution-card {
  border-radius: 12px;
}

.bucket-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bucket-row {
  display: grid;
  grid-template-columns: 60px 1fr;
  align-items: center;
  gap: 8px;
}

.bucket-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.jury-card {
  border-radius: 12px;
}

.experts-container {
  display: flex;
  justify-content: space-around;
  gap: var(--space-5);
  margin-bottom: var(--space-5);
  flex-wrap: wrap;
}

.expert-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  min-width: 180px;
  padding: 20px;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border-radius: 12px;
  transition: transform 0.2s, box-shadow 0.2s;

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
  }
}

.expert-avatar {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: var(--space-3);

  .avatar-circle {
    width: var(--avatar-size-lg);
    height: var(--avatar-size-lg);
    border-radius: var(--radius-circle);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: var(--font-weight-bold);
    font-size: var(--font-size-xl);
    margin-bottom: var(--space-2);
    color: var(--text-white);

    &.meme-expert { background: linear-gradient(135deg, #FF9A9E, #FECFEF); }
    &.emotion-expert { background: linear-gradient(135deg, #a18cd1, #fbc2eb); }
    &.legal-expert { background: linear-gradient(135deg, #84fab0, #8fd3f4); }
    &.default-expert { background: var(--bg-gray-2); }
  }

  .expert-name {
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    color: var(--text-primary);
  }
}

.expert-score {
  margin-bottom: var(--space-3);
  text-align: center;

  .score-label {
    display: block;
    font-size: var(--font-size-xs);
    color: var(--text-tertiary);
    margin-top: -10px;
  }
}

.expert-opinion {
  width: 100%;

  .opinion-bubble {
    background: var(--bg-white);
    padding: var(--space-2) var(--space-3);
    border-radius: var(--radius-lg);
    font-size: var(--font-size-xs);
    color: var(--text-secondary);
    line-height: 1.4;
    text-align: center;
    border: 1px solid var(--border-color);
    position: relative;

    &::before {
      content: '';
      position: absolute;
      top: -5px;
      left: 50%;
      transform: translateX(-50%);
      border-left: 5px solid transparent;
      border-right: 5px solid transparent;
      border-bottom: 5px solid var(--border-color);
    }
  }
}

.right-panels {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.sentiment-bars {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  padding: var(--space-2-5) 0;

  .bar-group {
    .label {
      font-size: var(--font-size-sm);
      color: var(--text-secondary);
      margin-bottom: var(--space-1-5);
      display: flex;
      justify-content: space-between;
    }
  }
}

.transparency-info {
  .info-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    padding: 12px;
    background: var(--bg-gray-1);
    border-radius: 8px;
    transition: background 0.2s;

    &:hover {
      background: var(--bg-hover);
    }

    .label {
      font-size: 13px;
      color: var(--text-secondary);
      font-weight: 500;
    }

    .value {
      font-size: 13px;
      color: var(--text-primary);
      font-weight: 600;
    }

    .trace-summary {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }
  }
}

.highlight-card {
  border-radius: 12px;
  
  :deep(.el-table) {
    border-radius: 8px;
    overflow: hidden;
  }
}

.risk-card {
  border-radius: 12px;
  
  :deep(.el-table) {
    border-radius: 8px;
    overflow: hidden;
  }
}

.interaction-management-card {
  border-radius: 12px;
  margin-top: 24px;
  
  .management-filters {
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
    flex-wrap: wrap;
    align-items: center;
  }
  
  .source-detail {
    display: flex;
    gap: 4px;
    flex-wrap: wrap;
  }
  
  .management-pagination {
    margin-top: 16px;
    display: flex;
    justify-content: center;
  }
  
  :deep(.el-table) {
    border-radius: 8px;
    overflow: hidden;
  }
}

.insight-alert {
  margin-top: var(--space-2-5);
}

@media (max-width: 900px) {
  .content-grid {
    grid-template-columns: 1fr;
  }

  .overview-card,
  .action-card,
  .distribution-card,
  .jury-card,
  .right-panels,
  .highlight-card,
  .risk-card {
    grid-column: 1 / -1;
  }

  .overview-metrics {
    grid-template-columns: 1fr;
  }
}
</style>
