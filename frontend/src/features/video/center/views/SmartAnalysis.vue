<template>
  <div class="smart-analysis">
    <div class="page-header">
      <div>
        <h2>视频智能分析报告</h2>
        <p>AI 全方位分析视频内容、互动氛围及潜在风险。</p>
      </div>
      <div class="header-actions">
        <el-tag v-if="progress && progress.status && progress.status !== 'idle'" type="info" effect="plain">
          重算进度：{{ progress.status }} {{ progress.progress ?? 0 }}%
        </el-tag>
        <el-button :loading="recomputeLoading" @click="triggerRecompute">手动触发重算</el-button>
        <el-button type="primary" :loading="juryLoading" @click="triggerJury">
          手动触发多智能体复核
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

      <!-- 风险详情 -->
      <el-card class="risk-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>风险/争议内容 (AI低分预警)</span>
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
import { ScaleToOriginal } from "@element-plus/icons-vue";

const route = useRoute();
const loading = ref(true);
const error = ref("");
const data = ref<any>(null);
const juryLoading = ref(false);
const recomputeLoading = ref(false);
const progress = ref<any>(null);
let progressTimer: number | null = null;

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
      ElMessage.success(res.message || "已触发重算");
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
      ElMessage.error(res.message || "触发失败");
    }
  } catch (err) {
    console.error(err);
    ElMessage.error("触发失败，请稍后再试");
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

onMounted(() => {
  fetchData();
  fetchProgress();
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

/* 情感分析卡片 */
.sentiment-card {
  grid-column: 2 / 3;
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

/* 风险卡片 */
.risk-card {
  grid-column: 1 / -1; /* 跨两列 */
}

.insight-alert {
  margin-top: var(--space-2-5);
}

/* 响应式 */
@media (max-width: 768px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
  
  .jury-card, .sentiment-card, .risk-card {
    grid-column: 1 / -1;
  }
}
</style>
