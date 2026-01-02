import { ref, watch, type Ref } from 'vue'; // 确保引入 Ref
import { ElMessage } from 'element-plus';
import { useUserStore } from "@/shared/stores/user";
import { toggleVideoLike, toggleVideoCollect } from "@/features/video/shared/api/video.api";
import type { Video } from "@/shared/types/entity";

// ✅ 修正：将类型定义为 Ref<Video | null | undefined> 以兼容所有情况
export function useVideoInteractions(videoData?: Ref<Video | null | undefined>) {
  const userStore = useUserStore();
  
  const isLiked = ref(false);
  const isCollected = ref(false);
  const likeCount = ref(0);
  const collectCount = ref(0);

  // 监听视频数据变化
  watch(() => videoData?.value, (newVal) => {
    // ✅ 增加非空检查 (newVal 可能是 null)
    if (newVal) {
      isLiked.value = !!newVal.is_liked;
      isCollected.value = !!newVal.is_collected;
      likeCount.value = newVal.like_count || 0;
      collectCount.value = newVal.collect_count || 0;
    }
  }, { immediate: true });

  const handleLike = async () => {
    if (!userStore.isLoggedIn) {
      ElMessage.warning('请先登录');
      return false;
    }
    
    const originalState = isLiked.value;
    const originalCount = likeCount.value;
    
    // 乐观更新
    isLiked.value = !isLiked.value;
    likeCount.value = isLiked.value ? likeCount.value + 1 : likeCount.value - 1;

    try {
      if (videoData?.value) {
        const response = await toggleVideoLike(videoData.value.id);
        // 使用后端返回的最新状态
        if (response.success && response.data) {
          isLiked.value = response.data.is_liked;
          likeCount.value = response.data.like_count;
          // 同步更新 videoData
          if (videoData.value) {
            videoData.value.is_liked = response.data.is_liked;
            videoData.value.like_count = response.data.like_count;
          }
          // 触发全局事件，通知其他页面更新数据
          window.dispatchEvent(new CustomEvent('video-like-changed', {
            detail: {
              videoId: videoData.value.id,
              isLiked: response.data.is_liked,
              likeCount: response.data.like_count
            }
          }));
        }
      }
    } catch (error) {
      // 回滚乐观更新
      isLiked.value = originalState;
      likeCount.value = originalCount;
      ElMessage.error('操作失败');
      return false;
    }
    return true;
  };

  const handleCollect = async (folderId?: number | null) => {
    if (!userStore.isLoggedIn) {
      ElMessage.warning('请先登录');
      return false;
    }

    // 如果已收藏，直接取消收藏
    if (isCollected.value) {
      const originalState = isCollected.value;
      const originalCount = collectCount.value;

      // 乐观更新
      isCollected.value = false;
      collectCount.value = collectCount.value - 1;

      try {
        if (videoData?.value) {
          const response = await toggleVideoCollect(videoData.value.id, undefined);
          if (response.success && response.data) {
            isCollected.value = response.data.is_collected;
            collectCount.value = response.data.collect_count;
            if (videoData.value) {
              videoData.value.is_collected = response.data.is_collected;
              videoData.value.collect_count = response.data.collect_count;
            }
            window.dispatchEvent(new CustomEvent('video-collect-changed', {
              detail: {
                videoId: videoData.value.id,
                isCollected: response.data.is_collected,
                collectCount: response.data.collect_count
              }
            }));
            ElMessage.success('取消收藏');
          }
        }
      } catch (error) {
        isCollected.value = originalState;
        collectCount.value = originalCount;
        ElMessage.error('操作失败');
        return false;
      }
      return true;
    }

    // 如果未收藏，需要选择文件夹（通过回调函数处理）
    // 这里返回一个标志，让调用者知道需要弹出文件夹选择对话框
    return 'need-folder-selection';
  };

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href);
    ElMessage.success('链接已复制到剪贴板');
  };

  return {
    isLiked,
    isCollected,
    likeCount,
    collectCount,
    handleLike,
    handleCollect,
    handleShare,
  };
}