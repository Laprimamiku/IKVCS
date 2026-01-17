<template>
  <div class="system-settings">
    <div class="page-header">
      <h2>
        <el-icon><Setting /></el-icon>
        系统设置
      </h2>
      <p class="subtitle">管理全局系统配置和限制</p>
    </div>

    <el-tabs v-model="activeTab" class="settings-tabs">
      <el-tab-pane label="功能开关" name="features">
        <el-card shadow="hover">
          <template #header>
            <span>功能开关</span>
          </template>
          <el-form :model="settings.features" label-width="200px">
            <el-form-item label="自动审核">
              <el-switch v-model="settings.features.auto_review_enabled" />
              <span class="form-desc">视频上传后自动进行AI审核</span>
            </el-form-item>
            <el-form-item label="高码率转码">
              <el-switch v-model="settings.features.high_bitrate_transcode_enabled" />
              <span class="form-desc">启用720p/1080p高码率转码</span>
            </el-form-item>
            <el-form-item label="AI分析">
              <el-switch v-model="settings.features.ai_analysis_enabled" />
              <span class="form-desc">启用AI内容分析功能</span>
            </el-form-item>
            <el-form-item label="多智能体">
              <el-switch v-model="settings.features.multi_agent_enabled" />
              <span class="form-desc">启用多智能体陪审团分析</span>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="文件限制" name="limits">
        <el-card shadow="hover">
          <template #header>
            <span>文件大小限制</span>
          </template>
          <el-form :model="settings.limits" label-width="200px">
            <el-form-item label="最大上传大小 (MB)">
              <el-input-number
                v-model="settings.limits.max_upload_size_mb"
                :min="100"
                :max="10240"
                :step="100"
              />
              <span class="form-desc">单个文件最大上传大小（MB）</span>
            </el-form-item>
            <el-form-item label="分片大小 (MB)">
              <el-input-number
                v-model="settings.limits.chunk_size_mb"
                :min="1"
                :max="50"
                :step="1"
              />
              <span class="form-desc">分片上传的每个分片大小（MB）</span>
            </el-form-item>
            <el-form-item label="视频最大帧数">
              <el-input-number
                v-model="settings.limits.max_frames_per_video"
                :min="10"
                :max="200"
                :step="10"
              />
              <span class="form-desc">每个视频最多提取的帧数量</span>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="转码配置" name="transcode">
        <el-card shadow="hover">
          <template #header>
            <span>转码配置</span>
          </template>
          <el-form :model="settings.transcode" label-width="200px">
            <el-form-item label="最大并发转码数">
              <el-input-number
                v-model="settings.transcode.max_concurrent"
                :min="1"
                :max="4"
                :step="1"
              />
              <span class="form-desc">同时进行的转码任务数量</span>
            </el-form-item>
            <el-form-item label="使用GPU加速">
              <el-switch v-model="settings.transcode.use_gpu" />
              <span class="form-desc">使用GPU硬件加速转码</span>
            </el-form-item>
            <el-form-item label="转码策略">
              <el-select v-model="settings.transcode.strategy">
                <el-option label="渐进式" value="progressive" />
                <el-option label="一次性" value="all" />
              </el-select>
              <span class="form-desc">progressive: 先转低清晰度；all: 一次性转所有清晰度</span>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <div class="action-bar">
      <el-button type="primary" :loading="saving" @click="handleSave">
        <el-icon><Check /></el-icon>
        保存设置
      </el-button>
      <el-button @click="handleReset">
        <el-icon><Refresh /></el-icon>
        重置
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { Setting, Check, Refresh } from "@element-plus/icons-vue";
import { adminApi } from "@/features/admin/api/admin.api";

const activeTab = ref("features");
const saving = ref(false);
const settings = ref({
  features: {
    auto_review_enabled: false,
    high_bitrate_transcode_enabled: false,
    ai_analysis_enabled: true,
    multi_agent_enabled: false,
  },
  limits: {
    max_upload_size_mb: 2048, // 2GB
    chunk_size_mb: 5,
    max_frames_per_video: 50,
  },
  transcode: {
    max_concurrent: 1,
    use_gpu: true,
    strategy: "progressive",
  },
});

const fetchSettings = async () => {
  try {
    const res = await adminApi.getSystemSettings();
    if (res.success && res.data) {
      // 转换数据格式
      settings.value = {
        features: {
          auto_review_enabled: res.data.auto_review_enabled ?? false,
          high_bitrate_transcode_enabled: res.data.high_bitrate_transcode_enabled ?? false,
          ai_analysis_enabled: res.data.ai_analysis_enabled ?? true,
          multi_agent_enabled: res.data.multi_agent_enabled ?? false,
        },
        limits: {
          max_upload_size_mb: Math.round((res.data.max_upload_size ?? 2147483648) / 1024 / 1024),
          chunk_size_mb: Math.round((res.data.chunk_size ?? 5242880) / 1024 / 1024),
          max_frames_per_video: res.data.max_frames_per_video ?? 50,
        },
        transcode: {
          max_concurrent: res.data.transcode_max_concurrent ?? 1,
          use_gpu: res.data.transcode_use_gpu ?? true,
          strategy: res.data.transcode_strategy ?? "progressive",
        },
      };
    }
  } catch (err: any) {
    console.error("获取系统设置失败:", err);
    ElMessage.error("获取系统设置失败");
  }
};

const handleSave = async () => {
  saving.value = true;
  try {
    const payload = {
      auto_review_enabled: settings.value.features.auto_review_enabled,
      high_bitrate_transcode_enabled: settings.value.features.high_bitrate_transcode_enabled,
      ai_analysis_enabled: settings.value.features.ai_analysis_enabled,
      multi_agent_enabled: settings.value.features.multi_agent_enabled,
      max_upload_size: settings.value.limits.max_upload_size_mb * 1024 * 1024,
      chunk_size: settings.value.limits.chunk_size_mb * 1024 * 1024,
      max_frames_per_video: settings.value.limits.max_frames_per_video,
      transcode_max_concurrent: settings.value.transcode.max_concurrent,
      transcode_use_gpu: settings.value.transcode.use_gpu,
      transcode_strategy: settings.value.transcode.strategy,
    };
    
    const res = await adminApi.updateSystemSettings(payload);
    if (res.success) {
      ElMessage.success("设置保存成功");
    } else {
      ElMessage.error(res.message || "保存失败");
    }
  } catch (err: any) {
    console.error("保存系统设置失败:", err);
    ElMessage.error("保存失败");
  } finally {
    saving.value = false;
  }
};

const handleReset = () => {
  fetchSettings();
  ElMessage.info("已重置为当前配置");
};

onMounted(() => {
  fetchSettings();
});
</script>

<style scoped lang="scss">
.system-settings {
  padding: 24px;
}

.page-header {
  margin-bottom: 24px;
  
  h2 {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 24px;
    margin: 0 0 8px 0;
  }
  
  .subtitle {
    color: var(--text-secondary);
    font-size: 14px;
    margin: 0;
  }
}

.settings-tabs {
  margin-bottom: 24px;
}

.form-desc {
  margin-left: 12px;
  font-size: 12px;
  color: var(--text-tertiary);
}

.action-bar {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding-top: 24px;
  border-top: 1px solid var(--border-color);
}
</style>

