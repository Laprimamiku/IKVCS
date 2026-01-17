<template>
  <div class="data-analysis">
    <div class="page-header">
      <div>
        <h2>数据分析</h2>
        <p>单个视频的数据统计与分析</p>
      </div>
      <el-button type="primary" link @click="fetchData">刷新</el-button>
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
      <!-- 数据总览 -->
      <el-card class="overview-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>数据总览</span>
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

      <!-- 质量分布 -->
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

      <!-- 情感分布 -->
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

      <!-- 高质量内容 -->
      <el-card class="highlight-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>高质量内容</span>
            <el-tag type="success" size="small">优先展示</el-tag>
          </div>
        </template>

        <el-table :data="highlightItems" style="width: 100%" stripe>
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
          <el-table-column prop="time" label="时间" width="180">
            <template #default="scope">
              {{ formatTime(scope.row.time) }}
            </template>
          </el-table-column>
        </el-table>

        <el-empty v-if="!highlightItems.length" description="暂无高质量内容" />
      </el-card>

      <!-- 风险内容 -->
      <el-card class="risk-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>风险/违规内容</span>
            <el-tag type="danger" size="small">AI预警</el-tag>
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
import { ref, onMounted, computed } from "vue";
import { useRoute } from "vue-router";
import { videoApi } from "@/features/video/shared/api/video.api";
import { ElMessage } from "element-plus";

const route = useRoute();
const loading = ref(true);
const error = ref("");
const data = ref<any>(null);

const governance = computed(() => data.value?.governance || {});
const overview = computed(() => governance.value?.overview || {});
const distribution = computed(() => governance.value?.distribution?.score_buckets || {});
const highlightItems = computed(() => governance.value?.exposure?.items || []);

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
  const total = Object.values(distribution.value).reduce((sum: number, v: any) => sum + (v || 0), 0);
  if (!total) return 0;
  return Math.round(((val || 0) / total) * 100);
};

const formatPercent = (val: number | null | undefined) => {
  if (val === null || val === undefined) return "0%";
  return `${(val * 100).toFixed(1)}%`;
};

const formatTime = (time: string | Date) => {
  if (!time) return "-";
  const date = new Date(time);
  return date.toLocaleString("zh-CN");
};

const getScoreColor = (score: number) => {
  if (score >= 80) return "#67C23A";
  if (score >= 60) return "#409EFF";
  if (score >= 40) return "#E6A23C";
  return "#F56C6C";
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
  } catch (err: any) {
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

onMounted(() => {
  fetchData();
});
</script>

<style scoped lang="scss">
.data-analysis {
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
}

.content-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  font-size: 16px;
}

.overview-card,
.distribution-card,
.sentiment-card,
.highlight-card,
.risk-card {
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

.sentiment-bars {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.bar-group {
  .label {
    font-size: 13px;
    color: var(--text-secondary);
    margin-bottom: 8px;
  }
}

:deep(.el-table) {
  border-radius: 8px;
  overflow: hidden;
}

@media (max-width: 768px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
  
  .overview-metrics {
    grid-template-columns: 1fr;
  }
}
</style>

