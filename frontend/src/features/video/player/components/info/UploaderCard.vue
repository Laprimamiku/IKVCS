<template>
  <div class="uploader-card" v-if="uploader">
    <div class="uploader-left">
      <el-avatar :size="48" :src="uploader.avatar" />
      <div class="uploader-text">
        <div class="name">{{ uploader.nickname }}</div>
        <div class="motto" :title="uploader.username">UP主</div>
      </div>
    </div>
    <el-button
      type="primary"
      size="small"
      class="follow-btn"
      @click="$emit('follow')"
    >
      关注
    </el-button>
  </div>
</template>

<script setup lang="ts">
import type { Video } from "@/shared/types/entity";

defineProps<{
  uploader: Video["uploader"] | null;
}>();

defineEmits<{
  follow: [];
}>();
</script>

<style lang="scss" scoped>
.uploader-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;

  .uploader-left {
    display: flex;
    align-items: center;
    gap: 12px;

    .uploader-text {
      .name {
        font-size: 15px;
        font-weight: 500;
        color: #18191c;
        margin-bottom: 2px;
        cursor: pointer;

        &:hover {
          color: #fb7299;
        }
      }

      .motto {
        font-size: 12px;
        color: #9499a0;
      }
    }
  }

  .follow-btn {
    background: #00aeec;
    border-color: #00aeec;
    padding: 8px 24px;

    &:hover {
      background: #00b5f5;
      border-color: #00b5f5;
    }
  }
}
</style>
