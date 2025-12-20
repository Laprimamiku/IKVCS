<template>
  <div class="smart-analysis">
    <div class="page-header">
      <h2>💡 互动智能分析</h2>
      <p>AI 实时洞察观众情绪，助你读懂每一条弹幕。</p>
    </div>

    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="5" animated />
    </div>

    <div v-else-if="error || !data" class="empty-state">
      <el-empty :description="error || '暂无分析数据'">
        <el-button type="primary" @click="fetchData">重试</el-button>
      </el-empty>
    </div>

    <div v-else class="content-grid">
      <el-card class="jury-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>⚖️ 专家陪审团诊断</span>
            <el-tag type="warning" size="small">深度层</el-tag>
          </div>
        </template>

        <div class="radar-chart-container">
          <div class="mock-radar">
            <div class="radar-label top">梗百科专家</div>
            <div class="radar-label right">法务专家</div>
            <div class="radar-label left">情感专家</div>
            <div class="radar-shape"></div>
            <div class="radar-stat">
              <div class="stat-num">92</div>
              <div class="stat-desc">综合健康分</div>
            </div>
          </div>
        </div>

        <el-alert
          :title="data.summary"
          type="info"
          show-icon
          :closable="false"
          class="insight-alert"
        />
      </el-card>

      <el-card class="sentiment-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>🎭 观众情绪分布</span>
            <el-tag type="success" size="small">实时</el-tag>
          </div>
        </template>

        <div class="sentiment-bars">
          <div class="bar-group">
            <div class="label">😍 喜爱/支持</div>
            <el-progress
              :percentage="calculatePercent(data.sentiment.positive)"
              :color="'#67C23A'"
              :format="() => data.sentiment.positive + '条'"
            />
          </div>
          <div class="bar-group">
            <div class="label">😐 中性/讨论</div>
            <el-progress
              :percentage="calculatePercent(data.sentiment.neutral)"
              :color="'#409EFF'"
              :format="() => data.sentiment.neutral + '条'"
            />
          </div>
          <div class="bar-group">
            <div class="label">😡 争议/负面</div>
            <el-progress
              :percentage="calculatePercent(data.sentiment.negative)"
              :color="'#F56C6C'"
              :format="() => data.sentiment.negative + '条'"
            />
          </div>
        </div>
      </el-card>

      <el-card class="risk-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <span>🛡️ 风险拦截记录 (AI自动识别)</span>
            <el-button type="primary" link @click="fetchData">刷新</el-button>
          </div>
        </template>

        <el-table :data="data.risks" style="width: 100%" stripe>
          <el-table-column prop="content" label="内容" min-width="200" />
          <el-table-column prop="reason" label="拦截原因" width="150">
            <template #default="scope">
              <el-tag type="danger">{{ scope.row.reason }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="score" label="AI评分" width="100">
            <template #default="scope">
              <span style="color: #f56c6c; font-weight: bold">{{
                scope.row.score
              }}</span>
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

// 计算百分比
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

const fetchData = async () => {
  const videoId = Number(route.params.videoId);
  if (!videoId) {
    error.value = "未指定视频ID";
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
      error.value = "登录已过期，请重新登录后查看";
      ElMessage.warning("请登录");
    } else {
      error.value = "网络错误或无权限";
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
.smart-analysis {
  padding: 20px;
}

.page-header {
  margin-bottom: 24px;
  h2 {
    font-size: 22px;
    margin-bottom: 8px;
    color: #303133;
  }
  p {
    color: #909399;
    font-size: 14px;
  }
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.risk-card {
  grid-column: 1 / -1;
}

.sentiment-bars {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 10px 0;

  .bar-group {
    .label {
      font-size: 14px;
      color: #606266;
      margin-bottom: 8px;
    }
  }
}

.radar-chart-container {
  height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 16px;

  .mock-radar {
    position: relative;
    width: 140px;
    height: 140px;

    .radar-shape {
      width: 100%;
      height: 100%;
      background: rgba(64, 158, 255, 0.1);
      border: 2px solid #409eff;
      transform: rotate(45deg);
    }

    .radar-label {
      position: absolute;
      font-size: 12px;
      color: #909399;
      white-space: nowrap;

      &.top {
        top: -25px;
        left: 50%;
        transform: translateX(-50%);
      }
      &.right {
        top: 50%;
        right: -60px;
        transform: translateY(-50%);
      }
      &.left {
        top: 50%;
        left: -60px;
        transform: translateY(-50%);
      }
    }

    .radar-stat {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      text-align: center;

      .stat-num {
        font-size: 24px;
        font-weight: bold;
        color: #303133;
      }
      .stat-desc {
        font-size: 12px;
        color: #909399;
      }
    }
  }
}

.insight-alert {
  margin-top: 10px;
}
</style>
