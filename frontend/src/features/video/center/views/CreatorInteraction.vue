<template>
  <div class="creator-interaction">
    <div class="page-header">
      <h1 class="page-title">
        <el-icon class="title-icon"><ChatDotRound /></el-icon>
        互动管理
      </h1>
      <div class="page-desc">管理您视频下的评论和弹幕</div>
    </div>

    <!-- 视频选择 -->
    <div class="video-selector">
      <el-select
        v-model="selectedVideoId"
        placeholder="选择要管理的视频"
        size="large"
        style="width: 100%; max-width: 500px;"
        @change="handleVideoChange"
      >
        <el-option
          v-for="video in videos"
          :key="video.id"
          :label="video.title"
          :value="video.id"
        >
          <div class="video-option">
            <span class="video-title">{{ video.title }}</span>
            <span class="video-stats">
              <el-icon><ChatDotRound /></el-icon>
              {{ video.comment_count || 0 }}
            </span>
          </div>
        </el-option>
      </el-select>
    </div>

    <!-- 评论管理 -->
    <div v-if="selectedVideoId" class="management-section">
      <el-tabs v-model="activeTab" class="management-tabs">
        <el-tab-pane label="评论管理" name="comments">
          <CommentManagement :video-id="selectedVideoId" />
        </el-tab-pane>
        <el-tab-pane label="弹幕管理" name="danmakus">
          <DanmakuManagement :video-id="selectedVideoId" />
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 未选择视频提示 -->
    <div v-else class="empty-prompt">
      <el-empty description="请选择一个视频开始管理评论和弹幕" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { ChatDotRound } from "@element-plus/icons-vue";
import CommentManagement from "@/features/video/center/components/CommentManagement.vue";
import DanmakuManagement from "@/features/video/center/components/DanmakuManagement.vue";
import type { Video } from "@/shared/types/entity";

const props = defineProps<{
  videos: Video[];
}>();

const selectedVideoId = ref<number | null>(null);
const activeTab = ref("comments");

const handleVideoChange = (videoId: number) => {
  selectedVideoId.value = videoId;
  activeTab.value = "comments";
};
</script>

<style lang="scss" scoped>
.creator-interaction {
  width: 100%;
}

.page-header {
  margin-bottom: var(--space-6);
  
  .page-title {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    font-size: var(--font-size-3xl);
    font-weight: var(--font-weight-semibold);
    color: var(--text-primary);
    margin: 0 0 var(--space-2);
    
    .title-icon {
      font-size: var(--font-size-4xl);
      color: var(--bili-blue);
    }
  }
  
  .page-desc {
    font-size: var(--font-size-base);
    color: var(--text-secondary);
  }
}

.video-selector {
  margin-bottom: var(--space-6);
}

.video-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  
  .video-title {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  
  .video-stats {
    display: flex;
    align-items: center;
    gap: var(--space-1);
    color: var(--text-secondary);
    font-size: var(--font-size-sm);
    margin-left: var(--space-4);
  }
}

.management-section {
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  box-shadow: var(--shadow-sm);
}

.empty-prompt {
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  padding: var(--space-16);
  box-shadow: var(--shadow-sm);
}
</style>


































