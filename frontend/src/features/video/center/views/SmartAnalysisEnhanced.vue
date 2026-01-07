<template>
  <div class="smart-analysis">
    <div class="page-header">
      <div>
        <h2>视频智能分析报告</h2>
        <p>AI 全方位分析视频内容、互动氛围及潜在风险。</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" :loading="juryLoading" @click="triggerJury">
          手动触发多智能体复核
        </el-button>
        <el-button type="success" :loading="recomputeLoading" @click="triggerRecompute">
          <el-icon><Refresh /></el-icon> 重新分析
        </el-button>
        <el-button type="primary" link @click="fetchData">刷新</el-button>
      </div>
    </div>

    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="5" animated />
    </div>

    <div v-else-if="error || !data" class="empty-state">
      <el-empty :description="error || '暂无分析数据'">
        <el-button type="primary" @click="fetchData">重新获取</el-button>
      </el-empty>
    </div>

    <div v-else class="content-grid">
      <!-- 陪审团分析 (Jury Trace View) -->
      <el-card class="jury-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>多智能体陪审团 (Multi-Agent Jury)</span>
            <div class="header-badges">
              <el-tag v-if="data.conflict_resolved" type="warning" effect="dark">
                <el-icon><ScaleToOriginal /></el-icon> Judge Agent 介入
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
              <span class="score-label">安全指数</span>
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

      <!-- 右侧信息面板 -->
      <div class="info-panels">
        <!-- 情感分布 -->
        <el-card class="sentiment-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>互动氛围情感分析</span>
              <el-tag type="success" size="small">实时</el-tag>
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

        <!-- 新增：透明度信息 -->
        <el-card class="transparency-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>分析透明度</span>
              <el-icon><InfoFilled /></el-icon>
            </div>
          </template>

          <div class="transparency-info">
            <div class="info-item">
              <span class="label">模型信息:</span>
              <span class="value">{{ data.model_info?.mode || 'unknown' }}</span>
            </div>
            <div class="info-item">
              <span class="label">Prompt版本:</span>
              <span class="value">
                弹幕: V{{ data.prompt_version?.danmaku?.id || 'N/A' }}
                评论: V{{ data.prompt_version?.comment?.id || 'N/A' }}
              </span>
            </div>
            <div class="info-item">
              <span class="label">成本统计:</span>
              <span class="value">{{ data.cost?.calls || 0 }} 次调用</span>
            </div>
            <div class="info-item">
              <span class="label">处理统计:</span>
              <div class="trace-summary">
                <el-tag size="small">规则: {{ data.decision_trace_summary?.rule_hits || 0 }}</el-tag>
                <el-tag size="small" type="success">缓存: {{ data.decision_trace_summary?.cache_hits || 0 }}</el-tag>
                <el-tag size="small" type="warning">云端: {{ data.decision_trace_summary?.cloud_calls || 0 }}</el-tag>
                <el-tag size="small" type="info">本地: {{ data.decision_trace_summary?.local_calls || 0 }}</el-tag>
              </div>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 风险详情 - 支持分页 -->
      <el-card class="risk-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>风险/争议内容 (AI低分预警)</span>
            <div class="header-actions">
              <el-button type="primary" size="small" @click="showItemsDialog = true">
                <el-icon><List /></el-icon> 查看明细
              </el-button>
              <el-button type="success" size="small" @click="triggerRecompute">
                <el-icon><Refresh /></el-icon> 重新分析
              </el-button>
            </div>
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
        </el-table>
      </el-card>
    </div>

    <!-- 新增：明细对话框 -->
    <el-dialog v-model="showItemsDialog" title="AI分析明细" width="80%" :before-close="handleItemsDialogClose">
      <div class="items-dialog-content">
        <div class="filter-bar">
          <el-select v-model="itemsFilter.type" placeholder="内容类型" clearable @change="fetchItems">
            <el-option label="弹幕" value="danmaku" />
            <el-option label="评论" value="comment" />
          </el-select>
          <el-select v-model="itemsFilter.filter" placeholder="筛选条件" clearable @change="fetchItems">
            <el-option label="风险内容" value="risk" />
            <el-option label="高亮内容" value="highlight" />
          </el-select>
          <el-input-number v-model="itemsFilter.scoreLt" placeholder="评分小于" :min="0" :max="100" @change="fetchItems" />
          <el-input-number v-model="itemsFilter.scoreGt" placeholder="评分大于" :min="0" :max="100" @change="fetchItems" />
        </div>

        <el-table :data="itemsList" style="width: 100%" v-loading="itemsLoading">
          <el-table-column prop="content" label="内容" min-width="200" show-overflow-tooltip />
          <el-table-column prop="type" label="类型" width="80">
            <template #default="scope">
              <el-tag size="small" :type="scope.row.type === 'danmaku' ? 'primary' : 'success'">
                {{ scope.row.type === 'danmaku' ? '弹幕' : '评论' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="score" label="评分" width="80">
            <template #default="scope">
              <span :style="{ color: getScoreColor(scope.row.score) }">{{ scope.row.score }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="ai_reason" label="AI分析" width="150" show-overflow-tooltip />
          <el-table-column prop="ai_confidence" label="置信度" width="100">
            <template #default="scope">
              {{ (scope.row.ai_confidence * 100).toFixed(1) }}%
            </template>
          </el-table-column>
          <el-table-column prop="ai_source" label="来源" width="100">
            <template #default="scope">
              <el-tag size="small" :type="getSourceTagType(scope.row.ai_source)">
                {{ getSourceLabel(scope.row.ai_source) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="时间" width="150">
            <template #default="scope">
              {{ formatTime(scope.row.created_at) }}
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination-wrapper">
          <el-pagination
            v-model:current-page="itemsPagination.page"
            v-model:page-size="itemsPagination.pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="itemsPagination.total"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="fetchItems"
            @current-change="fetchItems"
          />
        </div>
      </div>
    </el-dialog>

    <!-- 新增：重算进度对话框 -->
    <el-dialog v-model="showProgressDialog" title="重新分析进度" width="500px" :close-on-click-modal="false">
      <div class="progress-content">
        <el-progress 
          :percentage="recomputeProgress.progress" 
          :status="recomputeProgress.status === 'completed' ? 'success' : (recomputeProgress.status === 'failed' ? 'exception' : undefined)"
        />
        <p class="progress-message">{{ recomputeProgress.message }}</p>
        <div class="progress-details" v-if="recomputeProgress.details">
          <p>处理范围: {{ recomputeProgress.details.scope }}</p>
          <p>限制数量: {{ recomputeProgress.details.limit }}</p>
          <p>已处理: {{ recomputeProgress.details.processed || 0 }}</p>
          <p>错误数: {{ recomputeProgress.details.errors || 0 }}</p>
        </div>
      </div>
      <template #footer>
        <el-button @click="showProgressDialog = false" :disabled="recomputeProgress.status === 'running'">
          {{ recomputeProgress.status === 'running' ? '处理中...' : '关闭' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useRoute } from "vue-router";
import { videoApi } from "@/features/video/shared/api/video.api";
import { ElMessage } from "element-plus";
import { ScaleToOriginal, InfoFilled, List, Refresh } from "@element-plus/icons-vue";

const route = useRoute();
const loading = ref(true);
const error = ref("");
const data = ref<any>(null);
const juryLoading = ref(false);
const recomputeLoading = ref(false);

// 明细对话框相关
const showItemsDialog = ref(false);
const itemsList = ref([]);
const itemsLoading = ref(false);
const itemsFilter = ref({
  type: null,
  filter: null,
  scoreLt: null,
  scoreGt: null
});
const itemsPagination = ref({
  page: 1,
  pageSize: 20,
  total: 0
});

// 重算进度相关
const showProgressDialog = ref(false);
const recomputeProgress = ref({
  progress: 0,
  status: 'idle',
  message: '',
  details: null
});

// 总互动数
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
    case 'cache_exact':
    case 'cache_semantic':
      return 'success';
    case 'cloud_llm':
      return 'warning';
    case 'local_model':
      return 'info';
    case 'multi_agent':
      return 'danger';
    default:
      return '';
  }
};

const getSourceLabel = (source: string) => {
  const labels = {
    'cache_exact': '精确缓存',
    'cache_semantic': '语义缓存',
    'cloud_llm': '云端模型',
    'local_model': '本地模型',
    'multi_agent': '多智能体',
    'rule_hit': '规则匹配'
  };
  return labels[source] || source;
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
      error.value = "您无权查看此报告";
      ElMessage.warning("权限不足");
    } else {
      error.value = "系统繁忙，请稍后再试";
    }
  } finally {
    loading.value = false;
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
      ElMessage.success(res.message || "已触发多智能体复核");
      fetchData();
    } else {
      ElMessage.error(res.message || "触发失败");
    }
  } catch (err) {
    console.error(err);
    ElMessage.error("触发失败，请稍后再试");
  } finally {
    juryLoading.value = false;
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
    const res = await videoApi.triggerRecompute(videoId, { scope: "recent", limit: 200 });
    if (res.success) {
      ElMessage.success("重算任务已启动");
      showProgressDialog.value = true;
      recomputeProgress.value = res.data;
      
      // 轮询进度
      pollProgress(videoId);
    } else {
      ElMessage.error(res.message || "触发失败");
    }
  } catch (err) {
    console.error(err);
    ElMessage.error("触发失败，请稍后再试");
  } finally {
    recomputeLoading.value = false;
  }
};

const pollProgress = async (videoId: number) => {
  const pollInterval = setInterval(async () => {
    try {
      const res = await videoApi.getRecomputeProgress(videoId);
      if (res.success) {
        recomputeProgress.value = res.data;
        
        if (res.data.status === 'completed' || res.data.status === 'failed') {
          clearInterval(pollInterval);
          if (res.data.status === 'completed') {
            ElMessage.success("重算完成");
            fetchData(); // 刷新数据
          } else {
            ElMessage.error("重算失败");
          }
        }
      }
    } catch (err) {
      console.error("轮询进度失败", err);
      clearInterval(pollInterval);
    }
  }, 2000);
  
  // 30秒后停止轮询
  setTimeout(() => {
    clearInterval(pollInterval);
  }, 30000);
};

const fetchItems = async () => {
  const videoId = Number(route.params.videoId);
  if (!videoId) return;
  
  itemsLoading.value = true;
  try {
    const params = {
      item_type: itemsFilter.value.type,
      filter: itemsFilter.value.filter,
      score_lt: itemsFilter.value.scoreLt,
      score_gt: itemsFilter.value.scoreGt,
      page: itemsPagination.value.page,
      page_size: itemsPagination.value.pageSize
    };
    
    const res = await videoApi.getAnalysisItems(videoId, params);
    if (res.success) {
      itemsList.value = res.data.items;
      itemsPagination.value.total = res.data.total;
    }
  } catch (err) {
    console.error("获取明细失败", err);
    ElMessage.error("获取明细失败");
  } finally {
    itemsLoading.value = false;
  }
};

const handleItemsDialogClose = () => {
  showItemsDialog.value = false;
  // 重置筛选条件
  itemsFilter.value = {
    type: null,
    filter: null,
    scoreLt: null,
    scoreGt: null
  };
  itemsPagination.value.page = 1;
};

onMounted(() => {
  fetchData();
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

.header-badges, .header-actions {
  display: flex;
  gap: var(--space-2);
}

/* 陪审团卡片 */
.jury-card {
  grid-column: 1 / 2;
  
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
    padding: var(--space-4);
    background: var(--bg-gray-1);
    border-radius: var(--radius-lg);
    transition: transform var(--transition-base);
    
    &:hover {
      transform: translateY(-2px);
      box-shadow: var(--shadow-md);
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
}

/* 右侧信息面板 */
.info-panels {
  grid-column: 2 / 3;
  display: flex;
  flex-direction: column;
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

/* 透明度信息卡片 */
.transparency-info {
  .info-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    
    .label {
      font-size: 12px;
      color: var(--text-tertiary);
    }
    
    .value {
      font-size: 12px;
      color: var(--text-primary);
      font-weight: 500;
    }
    
    .trace-summary {
      display: flex;
      gap: 4px;
      flex-wrap: wrap;
    }
  }
}

/* 风险卡片 */
.risk-card {
  grid-column: 1 / -1; /* 跨两列 */
}

.insight-alert {
  margin-top: var(--space-2-5);
}

/* 明细对话框样式 */
.items-dialog-content {
  .filter-bar {
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
    flex-wrap: wrap;
  }
  
  .pagination-wrapper {
    margin-top: 16px;
    display: flex;
    justify-content: center;
  }
}

/* 进度对话框样式 */
.progress-content {
  .progress-message {
    margin: 16px 0;
    text-align: center;
    color: var(--text-secondary);
  }
  
  .progress-details {
    margin-top: 16px;
    padding: 12px;
    background: var(--bg-gray-1);
    border-radius: 6px;
    
    p {
      margin: 4px 0;
      font-size: 12px;
      color: var(--text-tertiary);
    }
  }
}

/* 响应式 */
@media (max-width: 768px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
  
  .jury-card, .info-panels, .risk-card {
    grid-column: 1 / -1;
  }
  
  .info-panels {
    flex-direction: row;
    gap: 12px;
  }
}
</style>